"""Repeat one reviewed silent picture until the exact end of a reviewed AAC soundtrack."""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from produce_live2d_short import REPO, run, sha256
from produce_music_visualizer import mux_and_verify, probe, validate_soundtrack


def picture_packets(path):
    return json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_packets",
        "-show_data_hash", "sha256", "-show_entries", "packet=pts,dts,duration,data_hash",
        "-of", "json", str(path),
    ], timeout=300))["packets"]


def validate_loops(movie, cycle, plan):
    frames = plan["frameCount"]
    audio = plan["audio"]
    step = audio["sampleRate"] // plan["fps"]
    last_duration = audio["durationSamples"] - (frames - 1) * step
    reference = picture_packets(cycle)
    packets = picture_packets(movie)
    if len(reference) != plan["videoLoop"]["frameCount"] or len(packets) != frames:
        raise ValueError("Loop packet counts differ from the plan.")
    for index, packet in enumerate(packets):
        pts = index * step
        duration = last_duration if index == frames - 1 else step
        if ((packet["pts"], packet["dts"], packet["duration"]) != (pts, pts, duration)
                or packet["data_hash"] != reference[index % len(reference)]["data_hash"]):
            raise ValueError(f"Loop packet or timestamp differs at frame {index}.")
    return len(packets)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("episode", "plan", "picture", "sound", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True)
    inputs = output / "inputs"
    inputs.mkdir()
    document = Path(shutil.copyfile(args.plan, inputs / "production-plan.json"))
    picture = Path(shutil.copyfile(args.picture, inputs / "original-picture.mp4"))
    sound = Path(shutil.copyfile(args.sound, inputs / "music.m4a"))
    plan = json.loads(document.read_bytes())
    if plan["schemaVersion"] != "vivhite-music-loop-1" or plan["chapters"]:
        raise ValueError("Expected a single-composition loop plan.")
    if sha256(picture) != plan["videoLoop"]["sha256"] or sha256(sound) != plan["audio"]["sha256"]:
        raise ValueError("Picture or soundtrack hash differs from the plan.")
    validate_soundtrack(plan, probe(sound)[0])
    [video] = probe(picture)
    fps = plan["fps"]
    window = plan["videoLoop"]["frameCount"]
    if (video["r_frame_rate"] != f"{fps}/1" or int(video["nb_frames"]) != window
            or (video["width"], video["height"]) != (plan["width"], plan["height"])):
        raise ValueError("Original picture dimensions or loop length differ from the plan.")
    run([
        sys.executable, str(REPO / "scripts/character_review.py"), "check",
        "--episode", str(args.episode), "--document", str(document),
        "--asset", str(picture), "--asset", str(sound),
    ], 60)
    rate = str(plan["audio"]["sampleRate"])
    cycle = output / "cycle.mp4"
    print("Preparing the original picture as a cuttable loop", flush=True)
    run([
        "ffmpeg", "-v", "error", "-xerror", "-i", str(picture), "-map", "0:v:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-bf", "0", "-pix_fmt", "yuv420p",
        "-map_metadata", "-1", "-map_chapters", "-1",
        "-video_track_timescale", rate, str(cycle),
    ], 600)
    timed = output / "looped-picture.mp4"
    frames = plan["frameCount"]
    run([
        "ffmpeg", "-v", "error", "-xerror", "-stream_loop", str((frames - 1) // window),
        "-i", str(cycle), "-map", "0:v:0", "-frames:v", str(frames), "-c:v", "copy",
        "-video_track_timescale", rate, str(timed),
    ], 900)
    print("Muxing the original audio and decoding the full delivery", flush=True)
    result = mux_and_verify(timed, output, plan, sound, stem="afterimage-single-loop")
    result["confirmedLoopPackets"] = validate_loops(output / result["filename"], cycle, plan)
    result["planSha256"] = sha256(document)
    (output / "delivery.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
