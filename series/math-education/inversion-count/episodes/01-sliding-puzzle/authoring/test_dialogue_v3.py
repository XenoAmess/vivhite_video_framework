"""Offline checks for evidence preservation and dialogue/action alignment."""
from __future__ import annotations

import copy
import json
import sys
import unittest

import compose_production_v3 as revised
from write_dialogue_docs_v3 import director_text


class DialogueRevisionTest(unittest.TestCase):
    def setUp(self):
        self.base = json.loads(revised.BASE_FILE.read_text(encoding="utf-8"))
        self.revision = json.loads(revised.REVISION_FILE.read_text(encoding="utf-8"))

    def apply(self, revision=None, base=None):
        return revised.revise(copy.deepcopy(base or self.base), self.base,
                              copy.deepcopy(revision or self.revision))

    def test_all_39_beats_preserve_mathematical_and_evidence_inputs(self):
        plan = self.apply()
        self.assertEqual(39, len(plan["beats"]))
        for old, new in zip(self.base["beats"], plan["beats"]):
            self.assertNotEqual(old["narration"], new["narration"])
            for field in ("view", "columns", "states", "goal", "knowledgePointIds",
                          "sourceSegmentIds", "styleMechanismIds", "formula", "labels", "note"):
                self.assertEqual(old.get(field), new.get(field), (old["id"], field))
            self.assertIn(new["narration"], director_text(plan))

    def test_missing_beat_and_state_override_are_rejected(self):
        missing = copy.deepcopy(self.revision)
        missing["beats"].pop()
        with self.assertRaisesRegex(ValueError, "all 39"):
            self.apply(missing)
        altered = copy.deepcopy(self.revision)
        altered["beats"][0]["states"] = [[1, 2, 3, 4, 5, 0]]
        with self.assertRaisesRegex(ValueError, "unreviewed field"):
            self.apply(altered)

    def test_missing_reversed_or_extra_move_cues_are_rejected(self):
        for mutation in ("missing", "reversed", "extra"):
            revision = copy.deepcopy(self.revision)
            entry = revision["beats"][4]
            if mutation == "missing":
                entry["moveCues"][0]["phrase"] = "this phrase is absent"
            elif mutation == "reversed":
                entry["moveCues"].reverse()
            else:
                entry["moveCues"].pop()
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.apply(revision)

    def test_all_cues_bind_through_actual_worker_with_synthetic_word_boundaries(self):
        sys.path.insert(0, str(revised.original.ROOT / "video-maker/tools"))
        import production_worker
        plan = self.apply()
        for beat in plan["beats"]:
            text = production_worker.letters(beat["narration"])
            # Synthetic boundaries exercise binding only; they are not TTS evidence.
            words = [{"text": char, "start": index * 0.3, "end": (index + 1) * 0.3}
                     for index, char in enumerate(text)]
            if beat.get("moveCues"):
                times = production_worker.action_times(beat, words, len(text) * 0.3 + 1)
                self.assertEqual(len(beat["states"]) - 1, len(times))
            production_worker.phrase_times(beat, words, beat.get("focusPairs", []))

    def test_route_narration_matches_every_actual_tile_direction(self):
        expected = {
            "b35": ["一向下", "三向右", "二也向右", "四向上", "五向左"],
            "b36": ["一向左", "三向下", "二向右", "把一向上滑", "五向右"],
            "b37": ["四向下", "一向左", "二再向左", "最后三向上"],
        }
        names = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五"}
        directions = {-3: "上", 3: "下", -1: "左", 1: "右"}
        route = []
        for beat in self.apply()["beats"]:
            if beat["id"] not in expected:
                continue
            self.assertEqual(expected[beat["id"]], [cue["phrase"] for cue in beat["moveCues"]])
            for before, after, cue in zip(beat["states"], beat["states"][1:], beat["moveCues"]):
                destination = before.index(0)
                source = after.index(0)
                name, direction = names[before[source]], directions[destination - source]
                self.assertIn(name, cue["phrase"])
                self.assertIn(direction, cue["phrase"])
            if not route:
                route.extend(beat["states"])
            else:
                self.assertEqual(route[-1], beat["states"][0])
                route.extend(beat["states"][1:])
        self.assertEqual(15, len(route))
        self.assertEqual([1, 2, 3, 4, 5, 0], route[-1])


if __name__ == "__main__":
    unittest.main()
