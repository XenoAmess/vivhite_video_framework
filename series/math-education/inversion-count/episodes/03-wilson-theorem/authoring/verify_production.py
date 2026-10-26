#!/usr/bin/env python3
"""Independently simulate every animation and check the exceptional proof cards."""
import argparse
import hashlib
import json
from pathlib import Path


def run(plan):
    outcomes = {}
    edge_swaps = algebra_cycles = 0
    for beat in plan["beats"]:
        proof = beat["proof"]
        names = [node["id"] for node in proof["nodes"]]
        labels = {node["id"]: node["label"] for node in proof["nodes"]}
        # Map initial position identities through the actual visual operations.
        state = {name: name for name in names}
        edges = {frozenset(edge) for edge in proof["edges"]}
        blank = proof.get("blank")
        for step in proof["steps"]:
            edges.update(frozenset(edge) for edge in step.get("addEdges", []))
            walk = step.get("walk", [])
            if walk:
                assert walk[0] == blank
                for a, b in zip(walk, walk[1:]):
                    assert frozenset((a, b)) in edges, (beat["id"], a, b)
                    state[a], state[b] = state[b], state[a]
                    edge_swaps += 1
                blank = walk[-1]
                assert blank == proof["root"], (beat["id"], "non-closed root card")
            for cycle in step.get("cycles", []):
                before = [state[name] for name in cycle]
                for target, value in zip(cycle[1:] + cycle[:1], before):
                    state[target] = value
                algebra_cycles += 1
        mapping = {origin: target for target, origin in state.items()}
        outcomes[beat["id"]] = mapping
    for beat_id, cycle in [("w18", ["z", "y", "c1"]),
                           ("w19a", ["z", "a4", "a1"]),
                           ("w19b", ["c1", "a4", "a1"]),
                           ("w28", ["inf", "0", "1", "2"])]:
        mapping = outcomes[beat_id]
        expected = dict(zip(mapping, mapping))
        expected.update(zip(cycle, cycle[1:] + cycle[:1]))
        assert mapping == expected, (beat_id, mapping, expected)
    assert {beat["sceneId"] for beat in plan["beats"]} == {f"s{i:02d}" for i in range(1, 39)}
    return {"passed": True, "scenes": 38, "beats": len(plan["beats"]),
            "proofSteps": sum(len(b["proof"]["steps"]) for b in plan["beats"]),
            "legalEdgeSwaps": edge_swaps, "algebraCycles": algebra_cycles,
            "exactCardChecks": ["w18", "w19a", "w19b", "w28"],
            "scope": "All authored visual operations, not a replacement for the symbolic infinite-family proof"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=Path(__file__).with_name("production-plan-v1.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source = args.plan.read_bytes()
    result = {"schemaVersion": "vivhite-production-math-check-1", "planSha256": hashlib.sha256(source).hexdigest(),
              **run(json.loads(source))}
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
