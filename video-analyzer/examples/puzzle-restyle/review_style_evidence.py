"""Reproducible diagnostics for the style re-review; no automatic similarity score."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def fingerprint(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def characters(text):
    return sum(character.isalpha() or character.isdecimal() for character in text)


def interval_characters(segments, start, end):
    # ASR does not give character-level truth. Boundary segments are apportioned by time.
    return sum(characters(segment["text"]) * max(0, min(end, segment["endMs"])
               - max(start, segment["startMs"])) / (segment["endMs"] - segment["startMs"])
               for segment in segments if segment["endMs"] > start and segment["startMs"] < end)


def measure(case, director):
    transcript_path = case / "style/transcript.json"
    transcript = read(transcript_path)
    script = read(director)
    body_end = 900240  # End of s00440, before the unconfirmed credits transcription.
    body = [segment for segment in transcript["segments"] if segment["startMs"] < body_end]
    reference_chars = interval_characters(body, 0, body_end)
    # This reviewed draft labels scene 20 as credits. Record the exclusion explicitly.
    scenes = script["scenes"]
    if [scene["id"] for scene in scenes] != [f"{index:02d}" for index in range(1, 21)]:
        raise ValueError("This diagnostic's draft-body boundary requires the original 20-scene draft")
    draft_end = scenes[-1]["startMs"]
    draft_chars = sum(characters(scene["narration"]) for scene in scenes[:-1])
    reference_cps = reference_chars * 1000 / body_end
    draft_cps = draft_chars * 1000 / draft_end
    ranges = [(0, 37000), (37460, 135600), (146140, 218300), (218300, 379340),
              (379820, 530940), (534600, 661480), (668700, 849320)]
    return {"schemaVersion": "1.0", "caseId": "puzzle-restyle", "reviewRevision": 2,
            "method": "Unicode letters/decimal digits divided by full interval, including pauses; not measured articulation rate",
            "boundaryMethod": "Crossing ASR segments apportioned linearly by overlapping duration",
            "reference": {"sourceSha256": transcript["identity"]["sourceSha256"],
                          "transcriptSha256": fingerprint(transcript_path), "bodyEndMs": body_end,
                          "includedAsrSegments": len(body), "characters": round(reference_chars, 3),
                          "grossCharactersPerSecond": round(reference_cps, 6),
                          "excludedSegments": [s["id"] for s in transcript["segments"] if s["startMs"] >= body_end]},
            "reviewedDraft": {"path": director.as_posix(), "sha256": fingerprint(director),
                              "bodyEndMs": draft_end, "excludedSceneIds": [scenes[-1]["id"]],
                              "characters": draft_chars, "grossCharactersPerSecond": round(draft_cps, 6),
                              "sceneCount": len(scenes), "medianSceneDurationMs": statistics.median(
                                  scene["endMs"] - scene["startMs"] for scene in scenes),
                              "sceneStatistics": [{"id": s["id"], "startMs": s["startMs"],
                                  "endMs": s["endMs"], "characters": characters(s["narration"])} for s in scenes]},
            "comparison": {"draftToReferenceGrossDensityRatio": round(draft_cps / reference_cps, 6),
                           "interpretation": "Draft has lower written narration density; this alone does not establish pacing or perceived similarity"},
            "referenceSections": [{"startMs": start, "endMs": end,
                "characters": round(interval_characters(body, start, end), 3),
                "grossCharactersPerSecond": round(interval_characters(body, start, end) * 1000 / (end - start), 6)}
                for start, end in ranges],
            "limitations": ["Reference text is unverified ASR; draft text has no synthesized voice recording.",
                            "ASR segments, semantic beats, director scenes and camera cuts are different units.",
                            "No inference about timbre, music, prosody or easing from text/image statistics."]}


def extract(case, output):
    import av
    from PIL import Image, ImageDraw, ImageFont

    source = read(case / "style/source.json")
    video = Path(source["path"])
    if fingerprint(video) != source["sha256"]:
        raise ValueError("Style video fingerprint mismatch")
    origin = read(case / "style/vision.json")["sourceOriginPtsMs"]
    ranges = [(37000, 114000), (379000, 411000), (689000, 745000), (801000, 850000)]
    frames = []
    (output / "frames").mkdir(parents=True, exist_ok=True)
    (output / "sheets").mkdir(exist_ok=True)
    for start, end in ranges:
        target = start
        with av.open(str(video)) as container:
            stream = next(s for s in container.streams.video if not (int(s.disposition) & 1024))
            stream.codec_context.thread_count = 4
            container.seek(int((start + origin) / (1000 * float(stream.time_base))), stream=stream)
            for frame in container.decode(stream):
                if frame.pts is None:
                    continue
                time_ms = round(float(frame.pts * stream.time_base) * 1000 - origin)
                if time_ms >= end:
                    break
                if time_ms < target:
                    continue
                name = f"frames/f{time_ms:09d}.jpg"
                frame.to_image().resize((1280, 720)).save(output / name, quality=88)
                frames.append({"timeMs": time_ms, "path": name, "requestedMs": target})
                target += 1000
        if target < end:
            raise ValueError(f"Dense interval {start}..{end} ended early")
        print(f"Extracted dense interval {start}..{end}", flush=True)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 21)
    sheets = []
    for offset in range(0, len(frames), 16):
        canvas = Image.new("RGB", (1944, 1240), "#222222")
        draw = ImageDraw.Draw(canvas)
        for index, item in enumerate(frames[offset:offset + 16]):
            x, y = 4 + index % 4 * 486, 4 + index // 4 * 310
            with Image.open(output / item["path"]) as picture:
                canvas.paste(picture.resize((480, 270)), (x, y + 30))
            seconds = item["timeMs"] / 1000
            draw.text((x, y), f"{int(seconds // 60):02d}:{seconds % 60:06.3f}", fill="white", font=font)
        path = f"sheets/dense-{len(sheets) + 1:03d}.jpg"
        canvas.save(output / path, quality=92)
        sheets.append({"path": path, "frames": frames[offset:offset + 16]})
    return {"sourceSha256": source["sha256"], "sampleIntervalMs": 1000,
            "intervals": [{"startMs": a, "endMs": b} for a, b in ranges],
            "frameCount": len(frames), "sheets": sheets,
            "scope": "Additional selected frames for four worked sequences; not full-frame or audio review"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-directory", type=Path, required=True)
    parser.add_argument("--director", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--extract", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    result = measure(args.case_directory, args.director)
    with (args.output / "pacing.json").open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    if args.extract:
        evidence = extract(args.case_directory, args.output)
        with (args.output / "dense-evidence.json").open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(evidence, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
