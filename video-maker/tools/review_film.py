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


def sample_manifest(plan: dict, timeline: dict) -> list[dict]:
    """Cover every authored stage/result while retaining explicit playback limits."""
    samples = []
    for beat, timing in zip(plan["beats"], timeline["beats"], strict=True):
        if beat["id"] != timing["id"]:
            raise ValueError("Evidence requires the actual matching beat timeline")
        start = timing["startFrame"] / timeline["fps"]
        duration = timing["frames"] / timeline["fps"]
        samples.append({"beatId": beat["id"], "kind": "beat_midpoint", "timeSeconds": start + duration * 0.56})
        for i, moment in enumerate(timing.get("moveTimes", [])):
            samples.append({"beatId": beat["id"], "kind": f"after_action_{i + 1}",
                            "timeSeconds": start + moment + 0.78})
        if beat.get("view") == "proof":
            steps = beat["proof"]["steps"]
            times = timing.get("visualTimes", [])
            if len(steps) != len(times):
                raise ValueError("Every proof step needs its real production time")
            for index, step in enumerate(steps):
                begin = times[index]
                end = times[index + 1] if index + 1 < len(times) else duration
                if not 0 <= begin < end <= duration:
                    raise ValueError("Invalid proof evidence interval")
                span = end - begin
                samples.append({"beatId": beat["id"], "kind": f"proof_step_{index + 1}_result",
                                "proofStep": index, "timeSeconds": start + begin + span * 0.9})
                edges = max(0, len(step.get("walk", [])) - 1)
                for edge in range(edges):
                    # Rendering reserves the final 18% of each submove for its settled state.
                    moment = begin + span * 0.75 * (edge + 0.90) / edges
                    samples.append({"beatId": beat["id"], "kind": f"proof_step_{index + 1}_slide_{edge + 1}",
                                    "proofStep": index, "walkEdge": edge,
                                    "timeSeconds": start + moment})
    samples.extend([{"beatId": "opening", "kind": "first", "timeSeconds": 0},
                    {"beatId": "closing", "kind": "last", "timeSeconds": timeline["durationSeconds"] - 1 / timeline["fps"]}])

    return samples


def review(directory: Path, ffmpeg: str = "ffmpeg") -> dict:
    film = directory / "film.mp4"
    plan = json.loads((directory / "production-plan.json").read_text(encoding="utf-8"))
    timeline = json.loads((directory / "timeline.json").read_text(encoding="utf-8"))
    output = directory / "encoded-review-frames"
    output.mkdir(exist_ok=True)
    samples = sample_manifest(plan, timeline)

    def extract(item):
        path = output / f"{item['beatId']}-{item['kind']}.png"
        if item["kind"] == "last":
            # Decode the short tail and reverse it: its first frame is the actual final
            # video frame, without scanning an hour-long film just to extract one image.
            argv = [ffmpeg, "-v", "error", "-y", "-sseof", "-2", "-i", str(film), "-vf", "reverse"]
        else:
            argv = [ffmpeg, "-v", "error", "-y", "-ss", str(item["timeSeconds"]), "-i", str(film)]
        result = subprocess.run([*argv, "-frames:v", "1", "-threads", "1", str(path)], timeout=45, capture_output=True)
        if result.returncode or not path.exists():
            raise RuntimeError(f"Frame extraction failed: {item}: " + result.stderr.decode("utf-8", "replace"))
        return {**item, "path": str(path.relative_to(directory)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    with ThreadPoolExecutor(max_workers=4) as pool:
        samples = list(pool.map(extract, samples))
    report = {"schemaVersion": "vivhite-encoded-frame-review-1", "filmSha256": hashlib.sha256(film.read_bytes()).hexdigest(),
              "coverage": "every beat, explicit action result, proof stage, proof walk result, first/last frame",
              "proofStageFrames": sum("proofStep" in sample and "walkEdge" not in sample for sample in samples),
              "proofWalkResultFrames": sum("walkEdge" in sample for sample in samples),
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
