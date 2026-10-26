"""Extract evidence from the encoded deliverable, bound to its exact bytes.

Creates selected-frame evidence, not a claim of exhaustive visual/human review.
Standard library + external FFmpeg only. GPL-3.0-only.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess


def review(directory: Path, ffmpeg: str = "ffmpeg") -> dict:
    film = directory / "film.mp4"
    plan = json.loads((directory / "production-plan.json").read_text(encoding="utf-8"))
    timeline = json.loads((directory / "timeline.json").read_text(encoding="utf-8"))
    output = directory / "encoded-review-frames"
    output.mkdir(exist_ok=True)
    samples = []
    for beat, timing in zip(plan["beats"], timeline["beats"], strict=True):
        start = timing["startFrame"] / timeline["fps"]
        duration = timing["frames"] / timeline["fps"]
        samples.append({"beatId": beat["id"], "kind": "beat_midpoint", "timeSeconds": start + duration * 0.56})
        for i, moment in enumerate(timing.get("moveTimes", [])):
            samples.append({"beatId": beat["id"], "kind": f"after_action_{i + 1}",
                            "timeSeconds": start + moment + 0.78})
    samples.extend([{"beatId": "opening", "kind": "first", "timeSeconds": 0},
                    {"beatId": "closing", "kind": "last", "timeSeconds": timeline["durationSeconds"] - 1 / timeline["fps"]}])

    def extract(item):
        path = output / f"{item['beatId']}-{item['kind']}.png"
        if item["kind"] == "last":
            # Concat container PTS may round a few ms; select the actual last frame by index.
            argv = [ffmpeg, "-v", "error", "-y", "-i", str(film), "-vf",
                    f"select=eq(n\\,{timeline['totalFrames'] - 1})"]
        else:
            argv = [ffmpeg, "-v", "error", "-y", "-ss", str(item["timeSeconds"]), "-i", str(film)]
        result = subprocess.run([*argv, "-frames:v", "1", "-threads", "1", str(path)], timeout=45, capture_output=True)
        if result.returncode or not path.exists():
            raise RuntimeError(f"Frame extraction failed: {item}: " + result.stderr.decode("utf-8", "replace"))
        return {**item, "path": str(path.relative_to(directory)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    with ThreadPoolExecutor(max_workers=4) as pool:
        samples = list(pool.map(extract, samples))
    report = {"schemaVersion": "vivhite-encoded-frame-review-1", "filmSha256": hashlib.sha256(film.read_bytes()).hexdigest(),
              "coverage": "one frame per beat, every explicit action result, first/last frame",
              "sampledFrames": len(samples), "totalFrames": timeline["totalFrames"],
              "humanFullPlayback": False, "samples": samples}
    (directory / "encoded-frame-evidence.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Extracted {len(samples)} encoded-deliverable frames")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    review(args.directory, args.ffmpeg)
