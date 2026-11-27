"""Render a reviewed, audio-reactive poster and mux the original AAC soundtrack."""

import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

from produce_live2d_short import REPO, TOOLS, run, sha256


def probe(path):
    return json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path),
    ], timeout=60))["streams"]


def audio_features(source, frame_count, fps):
    import numpy as np

    rate = 12000
    window_size = 1024
    mono = np.frombuffer(subprocess.check_output([
        "ffmpeg", "-v", "error", "-xerror", "-i", str(source),
        "-map", "0:a:0", "-ac", "1", "-ar", str(rate), "-f", "f32le", "-",
    ], timeout=360), dtype="<f4")
    hop = rate // fps
    padded = np.pad(mono, (window_size // 2, window_size))
    windows = np.lib.stride_tricks.sliding_window_view(padded, window_size)[::hop][:frame_count]
    if len(windows) != frame_count:
        raise ValueError("The soundtrack feature grid does not cover every picture frame.")
    frequencies = np.fft.rfftfreq(window_size, 1 / rate)
    bands = [(36, 155), (155, 420), (420, 1050), (1050, 2600), (2600, 5800)]
    masks = [(frequencies >= lo) & (frequencies < hi) for lo, hi in bands]
    taper = np.hanning(window_size).astype(np.float32)
    values = np.empty((frame_count, len(bands)), dtype=np.float32)
    for start in range(0, frame_count, 1024):
        page = windows[start:start + 1024] * taper
        power = np.abs(np.fft.rfft(page, axis=1)) ** 2
        values[start:start + len(page)] = np.stack(
            [np.log1p(np.sqrt(power[:, mask].mean(axis=1))) for mask in masks], axis=1,
        )
    lower, upper = np.percentile(values, [8, 97], axis=0)
    values = np.clip((values - lower) / np.maximum(1e-6, upper - lower), 0, 1)
    kernel = np.array([1, 2, 3, 4, 3, 2, 1], dtype=np.float32) / 16
    smooth = np.stack([np.convolve(band, kernel, mode="same") for band in values.T], axis=1)
    return smooth.astype("<f4"), len(mono)


def validate_soundtrack(plan, audio_stream):
    rate, samples, fps = plan["audio"]["sampleRate"], plan["audio"]["durationSamples"], plan["fps"]
    if (audio_stream["codec_name"] != "aac" or int(audio_stream["sample_rate"]) != rate
            or audio_stream["time_base"] != f"1/{rate}" or int(audio_stream["duration_ts"]) != samples
            or int(audio_stream["start_pts"]) != 0 or rate % fps
            or plan["frameCount"] != math.ceil(samples * fps / rate)):
        raise ValueError("Soundtrack format or timeline differs from the production plan.")


def validate_timeline(plan, audio_stream):
    validate_soundtrack(plan, audio_stream)
    if 12000 % plan["fps"]:
        raise ValueError("The picture frame rate must divide the feature sample rate.")
    cursor = 0
    for chapter in plan["chapters"]:
        if chapter["startFrame"] != cursor or chapter["endFrame"] <= cursor:
            raise ValueError("Chapters must cover the timeline in order without gaps or overlaps.")
        cursor = chapter["endFrame"]
    if cursor != plan["frameCount"]:
        raise ValueError("Chapter timeline does not cover the full soundtrack.")


def packet_streamhash(path):
    return subprocess.check_output([
        "ffmpeg", "-v", "error", "-xerror", "-i", str(path), "-map", "0:a:0",
        "-c:a", "copy", "-f", "streamhash", "-hash", "sha256", "-",
    ], timeout=180).decode("ascii").strip()


def mux_and_verify(timed, output, plan, sound, stem="afterimage-tide"):
    samples, rate, fps = plan["audio"]["durationSamples"], plan["audio"]["sampleRate"], plan["fps"]
    step = rate // fps
    chapters = plan["chapters"]
    chapter_input = []
    metadata = ["-map_metadata", "-1", "-map_chapters", "-1"]
    if chapters:
        chapters_file = output / "chapters.ffmeta"
        lines = [";FFMETADATA1"]
        for chapter in chapters:
            start = chapter["startFrame"] * step
            end = min(chapter["endFrame"] * step, samples)
            lines.extend(["[CHAPTER]", f"TIMEBASE=1/{rate}", f"START={start}", f"END={end}",
                          f"title={chapter['title']}"])
        chapters_file.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        chapter_input = ["-f", "ffmetadata", "-i", str(chapters_file)]
        metadata = ["-map_metadata", "2", "-map_chapters", "2"]
    last = plan["frameCount"] - 1
    tail = samples - step * last
    trim = f"setts=duration=if(eq(N\\,{last})\\,{tail}\\,DURATION)"
    candidate = output / f"{stem}.part.mp4"
    run([
        "ffmpeg", "-v", "error", "-xerror", "-i", str(timed), "-i", str(sound),
        *chapter_input, "-map", "0:v:0", "-map", "1:a:0", *metadata,
        "-metadata", f"title={plan['title']}", "-c", "copy",
        "-bsf:v", trim, "-video_track_timescale", str(rate),
        "-movflags", "+faststart", str(candidate),
    ], 600)
    video, audio, *_ = probe(candidate)
    if (video["codec_name"] != "h264" or video["pix_fmt"] != "yuv420p"
            or (video["width"], video["height"]) != (plan["width"], plan["height"])
            or video["r_frame_rate"] != f"{fps}/1" or int(video["nb_frames"]) != plan["frameCount"]
            or video["time_base"] != f"1/{rate}" or audio["time_base"] != f"1/{rate}"
            or int(video["start_pts"]) != 0 or int(audio["start_pts"]) != 0
            or int(video["duration_ts"]) != samples or int(audio["duration_ts"]) != samples):
        raise ValueError("Final MP4 dimensions, frame count or exact audiovisual duration did not match.")
    original_hash = packet_streamhash(sound)
    if original_hash != packet_streamhash(candidate):
        raise ValueError("AAC payload differs from the original soundtrack.")
    chapter_tags = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_chapters", "-of", "json", str(candidate),
    ], timeout=60))["chapters"]
    if [item["tags"]["title"] for item in chapter_tags] != [item["title"] for item in chapters]:
        raise ValueError("Final chapter names do not match the plan.")
    progress = subprocess.check_output([
        "ffmpeg", "-v", "error", "-xerror", "-i", str(candidate), "-map", "0:v:0", "-map", "0:a:0",
        "-progress", "pipe:1", "-nostats", "-f", "null", "-",
    ], timeout=1200).decode("ascii")
    last_decoded_count = int([line.split("=")[1] for line in progress.splitlines() if line.startswith("frame=")][-1])
    if last_decoded_count != plan["frameCount"] or not progress.rstrip().endswith("progress=end"):
        raise ValueError("Full audiovisual decode did not complete with the planned frame count.")
    movie = candidate.rename(output / f"{stem}.mp4")
    return {
        "filename": movie.name, "sha256": sha256(movie), "bytes": movie.stat().st_size,
        "durationSamples": samples, "sampleRate": rate, "decodedFrames": last_decoded_count,
        "aacPacketStreamHash": original_hash, "lastVideoFrameSamples": tail,
    }


def assemble(output, plan, sound):
    bytestream = output / "picture.h264"
    with bytestream.open("xb") as joined:
        for index in range(len(plan["chapters"])):
            with (output / "segments" / f"{index:02d}.h264").open("rb") as scene:
                shutil.copyfileobj(scene, joined, 1024 * 1024)
    timed = output / "picture-cfr.mp4"
    run([
        "ffmpeg", "-v", "error", "-xerror", "-r", str(plan["fps"]), "-i", str(bytestream),
        "-map", "0:v:0", "-c", "copy", "-video_track_timescale", str(plan["audio"]["sampleRate"]), str(timed),
    ], 600)
    return mux_and_verify(timed, output, plan, sound)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("episode", "plan", "portraits", "sound", "runtime", "chrome", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True)
    inputs = output / "inputs"
    inputs.mkdir()
    plan_path = Path(shutil.copyfile(args.plan, inputs / "production-plan.json"))
    art = Path(shutil.copyfile(args.plan.with_name("artwork.js"), inputs / "artwork.js"))
    sound = Path(shutil.copyfile(args.sound, inputs / "music.m4a"))
    plan = json.loads(plan_path.read_bytes())
    if plan["schemaVersion"] != "vivhite-music-art-1" or sha256(sound) != plan["audio"]["sha256"]:
        raise ValueError("Production schema or soundtrack hash mismatch.")
    validate_timeline(plan, probe(sound)[0])
    assets = [art, sound]
    for portrait in plan["portraits"].values():
        name = portrait["file"]
        if Path(name).name != name or not name.endswith(".png"):
            raise ValueError("Portrait file must be a PNG basename.")
        asset = Path(shutil.copyfile(args.portraits / name, inputs / name))
        if sha256(asset) != portrait["sha256"]:
            raise ValueError(f"Portrait hash mismatch: {name}")
        assets.append(asset)
    if not args.preview:
        run([
            sys.executable, str(REPO / "scripts/character_review.py"), "check",
            "--episode", str(args.episode), "--document", str(plan_path),
            *(value for asset in assets for value in ("--asset", str(asset))),
        ], 60)
    features, feature_samples = audio_features(sound, plan["frameCount"], plan["fps"])
    features.tofile(inputs / "features.f32")
    print(f"Analysed {feature_samples} mono samples for {len(features)} pictures", flush=True)
    run([
        "node", str(TOOLS / "render_music_visualizer.cjs"), str(args.runtime.resolve()),
        str(inputs), str(output), str(args.chrome.resolve()), "preview" if args.preview else "render",
    ], 5400)
    if not args.preview:
        print("Muxing the original AAC and decoding the complete output", flush=True)
        result = assemble(output, plan, sound)
        receipt = output / "delivery.json"
        receipt.write_text(json.dumps({
            "planSha256": sha256(plan_path), "audioFeatureFrames": len(features), **result,
        }, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(str(output / result["filename"]), flush=True)


if __name__ == "__main__":
    main()
