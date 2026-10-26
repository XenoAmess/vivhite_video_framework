"""Apply the reviewed full-episode dialogue revision to the original mathematics.

The v2 composer and delivery snapshot remain independent historical inputs.
This adapter does not synthesize speech, render video or grant semantic approval.
GPL-3.0-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import unicodedata

import compose_production as original


HERE = Path(__file__).resolve().parent
BASE_FILE = HERE / "production-plan-v2.json"
REVISION_FILE = HERE / "dialogue-v3.json"
MUTABLE_FIELDS = {"narration", "reaction", "action", "heading", "moveCues", "focusPairs"}
EDITORIAL_FIELDS = {"id", "issue", "reason"}


def letters(value: str) -> str:
    return "".join(char for char in value if unicodedata.category(char)[0] in "LN")


def validate_cues(beat: dict) -> None:
    """Check authored phrase presence/order without inventing real speech timings."""
    text = letters(beat["narration"])
    for field in ("moveCues", "focusPairs"):
        previous = (-1, -1.0)
        for cue in beat.get(field, []):
            phrase = letters(cue.get("phrase", ""))
            position = text.find(phrase)
            delay = cue.get("delay", 0)
            if not phrase or position < 0 or delay < 0:
                raise ValueError(f"Missing or invalid {field} phrase in {beat['id']}")
            current = (position, delay)
            if current <= previous:
                raise ValueError(f"Non-increasing {field} phrases in {beat['id']}")
            previous = current
    if "moveCues" in beat and len(beat["moveCues"]) != len(beat["states"]) - 1:
        raise ValueError(f"Move cue count mismatch in {beat['id']}")


def revise(plan: dict, base: dict, revision: dict) -> dict:
    if revision.get("schemaVersion") != "vivhite-dialogue-revision-1" or revision.get("revision") != 3:
        raise ValueError("Unsupported dialogue revision")
    base_beats = base["beats"]
    entries = revision["beats"]
    expected_ids = [beat["id"] for beat in base_beats]
    if len(expected_ids) != 39 or [beat["id"] for beat in plan["beats"]] != expected_ids:
        raise ValueError("The v3 review requires the original 39 action beats")
    if [entry["id"] for entry in entries] != expected_ids:
        raise ValueError("The dialogue revision must cover all 39 beats exactly once, in order")
    for beat, historical, entry in zip(plan["beats"], base_beats, entries):
        for field, value in historical.items():
            if field not in {"narration", "labels"} and beat.get(field) != value:
                raise ValueError(f"Historical beat changed before revision: {beat['id']} / {field}")
        labels = historical.get("labels")
        if labels is not None and beat["id"] == "b39" and plan["voice"]["name"] != "zh-CN-XiaoxiaoNeural":
            labels = [line.replace("Edge TTS 晓晓", "Edge TTS / " + plan["voice"]["name"]) for line in labels]
        if beat.get("labels") != labels:
            raise ValueError(f"Historical screen labels changed before revision: {beat['id']}")
        historical_narration = historical["narration"]
        if beat["id"] == "b39" and plan["voice"]["name"] != "zh-CN-XiaoxiaoNeural":
            historical_narration = historical_narration.replace("配音使用晓晓。", "配音使用当前配置的声音。")
        if beat["narration"] != historical_narration:
            raise ValueError(f"Historical narration changed before revision: {beat['id']}")
        if set(entry) - MUTABLE_FIELDS - EDITORIAL_FIELDS:
            raise ValueError(f"Dialogue revision tries to change an unreviewed field: {beat['id']}")
        if not all(isinstance(entry.get(key), str) and entry[key].strip()
                   for key in ("narration", "issue", "reason")):
            raise ValueError(f"Incomplete dialogue review in {beat['id']}")
        for key in MUTABLE_FIELDS & entry.keys():
            beat[key] = entry[key]
        if beat["id"] == "b39" and plan["voice"]["name"] != "zh-CN-XiaoxiaoNeural":
            beat["narration"] = beat["narration"].replace("配音使用晓晓。", "配音使用当前配置的声音。")
        validate_cues(beat)
    plan["revision"] = 3
    plan["provenance"]["authoring"] = "assistant_authored_v3"
    plan["provenance"]["baseProductionPlanSha256"] = revision["basePlanSha256"]
    return plan


def compose(analysis_path: Path, math_path: Path, voice: str = "zh-CN-XiaoxiaoNeural",
            rate: str = "+8%", video_codec: str = "h264_nvenc") -> dict:
    revision_bytes = REVISION_FILE.read_bytes()
    revision = json.loads(revision_bytes)
    base_bytes = BASE_FILE.read_bytes()
    if hashlib.sha256(base_bytes).hexdigest() != revision["basePlanSha256"]:
        raise ValueError("The historical v2 delivery snapshot no longer matches the review baseline")
    plan = original.compose(analysis_path, math_path, voice, rate, video_codec)
    plan = revise(plan, json.loads(base_bytes), revision)
    plan["provenance"]["dialogueRevisionSha256"] = hashlib.sha256(revision_bytes).hexdigest()
    return plan


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("analysis", type=Path)
    parser.add_argument("math", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
    parser.add_argument("--rate", default="+8%")
    parser.add_argument("--video-codec", default="h264_nvenc", choices=["libx264", "h264_nvenc"])
    args = parser.parse_args()
    historical_output = args.output.resolve() == BASE_FILE.resolve()
    if historical_output or args.output.name in {"authored-plan.json", "production-plan.json"} and "production-v2" in str(args.output.parent):
        raise ValueError("Refusing to overwrite a historical v2 delivery")
    plan = compose(args.analysis, args.math, args.voice, args.rate, args.video_codec)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Composed {len(plan['beats'])} revised action beats; no speech or video produced")
