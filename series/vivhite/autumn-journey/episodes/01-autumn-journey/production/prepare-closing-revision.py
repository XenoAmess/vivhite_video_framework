"""Prepare a separate six-second closing revision; never grants semantic approval.

Run reference_finisher.finish only after reviewing the prepared assets and plan.
GPL-3.0-only.
"""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import shutil

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[4]
spec = importlib.util.spec_from_file_location("reference_finisher", ROOT / "video-maker/tools/reference_finisher.py")
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


def prepare(previous, destination):
    previous, destination = previous.resolve(), destination.resolve()
    if (previous == destination or destination.is_relative_to(previous)
            or previous.is_relative_to(destination) or (destination / "film.mp4").exists()):
        raise ValueError("Use a separate run without an existing delivered film")
    baseline_file = EP / "final-assembly-plan-v4.json"
    baseline = json.loads(baseline_file.read_text(encoding="utf-8"))
    expected_film = "204570851392316fe7e3f797388464227b61662288aa2a32c0a078d657e7ed22"
    if worker.sha(previous / "film.mp4") != expected_film:
        raise ValueError("Previous delivery changed")
    destination.mkdir(parents=True, exist_ok=True)
    for item in baseline["files"]:
        path = Path(item["path"])
        source, target = previous / path, destination / path
        if path.is_absolute() or not source.resolve().is_relative_to(previous) or not target.resolve().is_relative_to(destination):
            raise ValueError("Input path escaped its run")
        if worker.sha(source) != item["sha256"]:
            raise ValueError("Previous approved input changed")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    retimed = destination / "retimed/S48-slow-v1.mp4"
    retimed.parent.mkdir(exist_ok=True)
    parent = "clean-text-001/sources/S48.mp4"
    filters = "trim=end_frame=22,setpts=8*(PTS-STARTPTS),minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:vsbmc=1:scd=none"
    if not retimed.exists():
        worker.run(["ffmpeg", "-v", "error", "-y", "-i", str(destination / parent), "-an", "-vf", filters,
                    "-frames:v", "144", "-c:v", "libx264", "-preset", "medium", "-crf", "16",
                    "-pix_fmt", "yuv420p", str(retimed)])
    probe = json.loads(worker.run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-of", "json", str(retimed)]))
    stream = probe["streams"][0]
    if (int(stream["nb_read_frames"]) != 144 or stream["avg_frame_rate"] != "24/1"
            or (stream["width"], stream["height"]) != (832,480) or len(probe["streams"]) != 1):
        raise ValueError("Unexpected retimed clip format")
    worker.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(retimed), "-f", "null", "-"])
    receipt = {"schemaVersion":"vivhite-closing-retime-1", "parent":parent,
               "parentSha256":worker.sha(destination / parent), "output":retimed.relative_to(destination).as_posix(),
               "outputSha256":worker.sha(retimed), "speedMultiplier":0.125, "timeStretchFactor":8,
               "filter":filters, "outputFrames":144, "fps":24, "durationSeconds":6,
               "wholeSceneSlowed":True, "audioUsed":False,
               "scope":"Technical transform only; all output frames require semantic review."}
    worker.write_json(destination / "closing-retime-receipt.json", receipt)

    # Copy the unchanged 196 seconds as picture packets; the final finisher encodes
    # the full film using the same soundtrack, title timing and closing fade.
    worker.run(["ffmpeg", "-v", "error", "-y", "-i", str(previous / baseline["pictureFile"]),
                "-map", "0:v:0", "-frames:v", "5880", "-c", "copy", str(destination / "prefix-picture.mp4")])
    worker.run(["ffmpeg", "-v", "error", "-y", "-i", str(retimed), "-an", "-vf",
                "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30",
                "-frames:v", "180", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-pix_fmt", "yuv420p", str(destination / "closing-picture.mp4")])
    (destination / "closing-picture.ffconcat").write_text(
        "ffconcat version 1.0\nfile 'prefix-picture.mp4'\nfile 'closing-picture.mp4'\n", encoding="utf-8", newline="\n")
    picture = "picture-assembly-closing-v4.mp4"
    worker.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "closing-picture.ffconcat",
                "-c", "copy", "-movflags", "+faststart", picture], cwd=destination)
    picture_probe = json.loads(worker.run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-of", "json", str(destination / picture)]))
    if int(picture_probe["streams"][0]["nb_read_frames"]) != 6060:
        raise ValueError("Picture assembly changed the episode frame count")

    final = copy.deepcopy(baseline)
    final["pictureFile"] = picture
    final["closingCredit"] = ""
    overlay = next(row for row in final["titleOverlays"] if row["shotId"] == "S48")
    overlay.update(text="白绮|秋日旅程", subtitle="献给最可爱的你")
    closing = final["shots"][-1]
    assert closing["id"] == "S48" and closing["startFrame"] == 5880
    closing.update(sourceFile=receipt["output"], sourceSeconds=6,
                   action="无人海岸宽景，小蓝蝶平静而缓慢地开合翅膀；天空只叠两行：白绮|秋日旅程、献给最可爱的你。末尾随画面淡下。",
                   postprocess={"receipt":"closing-retime-receipt.json", "speedMultiplier":0.125,
                                "wholeSceneSlowed":True, "frameInterpolation":"FFmpeg motion compensated, 24fps"})
    final["revision"] = {"id":"closing-v4-001", "baselinePlanSha256":worker.sha(baseline_file),
                         "baselineFilmSha256":expected_film, "changedShots":["S48"],
                         "unchangedShotCount":47, "sourcePlanSha256Meaning":"Original model generation plan; retiming is bound separately."}
    (destination / "titles.ass").write_text(worker.titles(final), encoding="utf-8-sig", newline="\n")
    decisions = json.loads((destination / "clip-decisions.json").read_text(encoding="utf-8"))
    decision = decisions["shots"][-1]
    assert decision["id"] == "S48"
    decision.update(sourceSha256=receipt["outputSha256"], method="pending-assistant-frame-review",
                    allUsedFrameReview=False, reviewedNativeFrames=0, frameEvidence=[],
                    observation="New slow-motion source awaits review; previous source acceptance does not carry over.")
    for key in ("noHumanFaces", "noAddedPeople", "allCharactersFemale", "costumeStyle", "motionAndContinuity", "merchandiseBehavior"):
        decision[key] = "pending"
    worker.write_json(destination / "clip-decisions.json", decisions)
    selections = json.loads((destination / "source-selections.json").read_text(encoding="utf-8"))
    selections["selections"]["S48"] = {"path":receipt["output"], "sha256":receipt["outputSha256"],
        "parent":parent, "parentSha256":receipt["parentSha256"], "receipt":"closing-retime-receipt.json"}
    worker.write_json(destination / "source-selections.json", selections)
    paths = [item["path"] for item in final["files"] if item["path"] != baseline["pictureFile"]]
    paths.extend([picture, receipt["output"], "closing-retime-receipt.json"])
    final["files"] = [{"path":path, "sha256":worker.sha(destination / path)} for path in dict.fromkeys(paths)]
    worker.write_json(EP / "final-assembly-plan-v5.json", final)
    print("Prepared separate revision. New S48 remains pending actual frame review.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    prepare(args.previous, args.destination)
