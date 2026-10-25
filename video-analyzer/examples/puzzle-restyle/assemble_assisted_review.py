"""Assemble this case's authored notes; this is not an automatic semantic reviewer.

Un-overridden unit meanings preserve ASR wording with an explicit context reference.
They must not be presented as word-perfect audio verification.
"""
import argparse
import json
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def assemble(directory, notes):
    workspace = read(directory / "workspace.json")
    actual_hashes = {role: source["sha256"] for role, source in workspace["sources"].items()}
    if notes["sourceHashes"] != actual_hashes:
        raise ValueError("Authored case notes belong to different source videos")
    bundle = {"schemaVersion": "1.0", "caseId": workspace["caseId"],
              "provenance": notes["provenance"],
              "sourceHashes": {role: source["sha256"] for role, source in workspace["sources"].items()},
              "contentAnalysis": notes["contentAnalysis"], "styleAnalysis": notes["styleAnalysis"],
              "adaptationNotes": notes["adaptationNotes"], "windowReviews": []}
    for entry in workspace["packets"]:
        packet = read(directory / entry["path"])
        role = entry["role"]
        index = int(entry["id"].split("w")[-1]) - 1
        note = notes["windows"][role][index]
        units = []
        for unit in packet["units"]:
            override = notes.get("unitOverrides", {}).get(role + ":" + unit["id"])
            issues = list(note.get("issues", []))
            raw = unit["text"].strip()
            if override:
                meaning = override["meaning"]
                issues.extend(override.get("issues", []))
            else:
                meaning = raw
                issues.append("保留 ASR 字面记录；句间指代和语义见本窗口摘要，未逐句听音校准。")
            units.append({"segmentId": unit["id"], "meaning": meaning, "issues": issues,
                          "annotationMethod": "authored_override" if override else "asr_with_window_context"})
        frames = packet["frames"]
        bundle["windowReviews"].append({"windowId": entry["id"], "summary": note["summary"],
              "unitReviews": units, "visualFindings": [
                  {"frameId": frame["id"], "observation": note["visual"] + "（所在连续窗口的组图观察；不推断两帧间瞬时动作。）"}
                  for frame in frames]})
    return bundle


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("notes", type=Path)
    args = parser.parse_args()
    result = assemble(args.directory, read(args.notes))
    (args.directory / "review-bundle.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
