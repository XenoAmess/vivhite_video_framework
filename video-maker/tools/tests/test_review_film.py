"""Check whole-stage evidence planning without encoding or network access."""
import importlib.util
from pathlib import Path
import unittest


SPEC = importlib.util.spec_from_file_location("review_film", Path(__file__).parents[1] / "review_film.py")
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)


class EncodedEvidenceTest(unittest.TestCase):
    def test_every_proof_stage_and_legal_move_receives_a_settled_frame(self):
        plan = {"beats": [{"id": "proof1", "view": "proof", "proof": {"steps": [
            {"walk": ["x", "a", "b", "x"]}, {"rows": ["result"]}]}}]}
        timeline = {"fps": 30, "durationSeconds": 20, "totalFrames": 600,
                    "beats": [{"id": "proof1", "startFrame": 0, "frames": 600, "visualTimes": [0, 12]}]}
        result = review.sample_manifest(plan, timeline)
        self.assertEqual(sum("walkEdge" in sample for sample in result), 3)
        self.assertEqual(sum("proofStep" in sample and "walkEdge" not in sample for sample in result), 2)
        self.assertAlmostEqual(next(s["timeSeconds"] for s in result if s.get("walkEdge") == 0), 2.7)
        self.assertTrue(all(0 <= sample["timeSeconds"] < 20 for sample in result))

    def test_missing_stage_times_or_wrong_beat_is_rejected(self):
        plan = {"beats": [{"id": "p", "view": "proof", "proof": {"steps": [{}]}}]}
        timeline = {"fps": 30, "durationSeconds": 5, "totalFrames": 150,
                    "beats": [{"id": "p", "startFrame": 0, "frames": 150}]}
        with self.assertRaisesRegex(ValueError, "Every proof step"):
            review.sample_manifest(plan, timeline)
        timeline["beats"][0]["id"] = "wrong"
        with self.assertRaisesRegex(ValueError, "matching beat"):
            review.sample_manifest(plan, timeline)


if __name__ == "__main__":
    unittest.main()
