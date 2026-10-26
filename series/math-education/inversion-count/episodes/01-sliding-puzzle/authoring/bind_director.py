"""Bind an authored director draft to the exact validated analysis artifact."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("analysis", type=Path)
parser.add_argument("template", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
analysis = json.loads(args.analysis.read_text(encoding="utf-8"))
if analysis.get("validationStatus") != "structural_and_evidence_coverage_passed":
    raise ValueError("Analysis has not passed coverage validation")
script = json.loads(args.template.read_text(encoding="utf-8"))
if script["sourceHashes"] != analysis.get("sourceHashes"):
    raise ValueError("This authored director template belongs to different source videos")
script["analysisSha256"] = hashlib.sha256(args.analysis.read_bytes()).hexdigest()
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(script, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
