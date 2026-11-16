"""Offline checks of exact timing, title control characters and reviewed inputs."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import wave

SPEC = importlib.util.spec_from_file_location("reference_finisher", Path(__file__).parents[1]/"reference_finisher.py")
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


class ReferenceFinisherTest(unittest.TestCase):
    def test_finalization_cannot_accept_unresolved_or_changed_video(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = {"sourcePlanSha256":"plan", "shots":[{"id":"S02", "seconds":3}],
                    "files":[{"path":"sources/S02.mp4", "sha256":"video"}]}
            row = {"id":"S02", "sourceSha256":"video", "method":"assistant-frame-review",
                   "allUsedFrameReview":True, "reviewedNativeFrames":72,
                   **{k:"passed" for k in ("noHumanFaces","noAddedPeople","allCharactersFemale","costumeStyle",
                                          "motionAndContinuity","merchandiseBehavior")}}
            decisions = {"schemaVersion":"vivhite-clip-decisions-1", "sourcePlanSha256":"plan", "shots":[row]}
            file = root/"clip-decisions.json"
            file.write_text(json.dumps(decisions), encoding="utf-8")
            worker.verify_clip_decisions(plan, root)
            plan['referenceAppearanceRequired'] = True
            with self.assertRaisesRegex(ValueError,'artwork appearance'):
                worker.verify_clip_decisions(plan, root)
            row['referenceAppearance'] = 'passed'
            file.write_text(json.dumps(decisions), encoding='utf-8')
            worker.verify_clip_decisions(plan, root)
            plan.pop('referenceAppearanceRequired')
            for field, bad in (("noHumanFaces","failed"),("noAddedPeople","failed"),
                               ("sourceSha256","replaced"),("allUsedFrameReview",False)):
                altered = json.loads(json.dumps(decisions))
                altered["shots"][0][field] = bad
                file.write_text(json.dumps(altered), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "acceptance"):
                    worker.verify_clip_decisions(plan, root)

    def test_reviewed_inputs_reject_replacement_and_path_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/"source.mp4").write_bytes(b"reviewed source")
            plan = {"files":[{"path":"source.mp4", "sha256":worker.sha(root/"source.mp4")}]}
            self.assertEqual(worker.bound_files(plan, root), [root/"source.mp4"])
            (root/"source.mp4").write_bytes(b"replacement")
            with self.assertRaisesRegex(ValueError, "changed"):
                worker.bound_files(plan, root)
            plan["files"][0]["path"] = "../outside.mp4"
            with self.assertRaises(ValueError):
                worker.bound_files(plan, root)

    def test_titles_stay_inside_shot_without_dialogue_or_extra_tail(self):
        plan = {"fps":30, "shots":[{"id":"S06", "startFrame":600, "seconds":4},
                                   {"id":"S48", "startFrame":5880, "seconds":6}],
                "titleOverlays":[{"shotId":"S06", "text":"白绮／秋日旅程", "subtitle":"Vivhite · Autumn Journey"},
                                 {"shotId":"S48", "text":"白绮／秋日旅程", "subtitle":"Vivhite · Autumn Journey"}]}
        result = worker.titles(plan)
        self.assertIn("0:00:20.40,0:00:23.65", result)
        self.assertIn("0:03:16.40,0:03:21.65", result)
        self.assertEqual(result.count("Dialogue: "), 5, "ASS events are titles/credits only")
        plan["titleOverlays"][0]["text"] = "bad{\\pos(1,2)}"
        with self.assertRaises(ValueError):
            worker.titles(plan)

    def test_synthetic_soundtrack_has_exact_samples_and_no_recorded_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            plan = {"fps":30, "totalFrames":60, "shots":[{"id":"S01", "startFrame":0,
                     "seconds":2, "soundDescription":"风、水"}]}
            receipt = worker.synthesize(plan, Path(temporary), seed=17)
            with wave.open(str(Path(temporary)/"soundtrack.wav"), "rb") as audio:
                self.assertEqual(audio.getnframes(), 96000)
                self.assertEqual((audio.getnchannels(), audio.getframerate()), (2, 48000))
            self.assertEqual(receipt["speechSource"], "none")
            self.assertIs(receipt["nativeModelAudioInFinalMix"], False)

    def test_closing_dedication_can_replace_subtitle_and_suppress_credits(self):
        plan = {"fps":30, "shots":[{"id":"S48", "startFrame":5880, "seconds":6}],
                "titleOverlays":[{"shotId":"S48", "text":"白绮|秋日旅程", "subtitle":"献给最可爱的你"}],
                "closingCredit":""}
        events = [line for line in worker.titles(plan).splitlines() if line.startswith("Dialogue:")]
        self.assertEqual(len(events), 2)
        self.assertTrue(events[0].endswith("白绮|秋日旅程"))
        self.assertTrue(events[1].endswith("献给最可爱的你"))
        self.assertFalse(any(",Credit," in line for line in events))
        plan["closingCredit"] = "bad{\\pos(1,2)}"
        with self.assertRaises(ValueError):
            worker.titles(plan)

    def test_native_delivery_dimensions_do_not_silently_fall_back_to_1080p(self):
        self.assertEqual(worker.output_dimensions({}),(1920,1080))
        self.assertEqual(worker.output_dimensions({"width":1344,"height":768}),(1344,768))
        self.assertEqual(worker.output_dimensions({"width":2560,"height":1440}),(2560,1440))
        with self.assertRaisesRegex(ValueError,"dimensions"):
            worker.output_dimensions({"width":1344,"height":1080})


if __name__ == "__main__":
    unittest.main()
