"""Offline tests for audio/caption timing; no paid or live synthesis."""
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave

SPEC = importlib.util.spec_from_file_location("production_worker", Path(__file__).parents[1] / "production_worker.py")
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


class ProductionWorkerTest(unittest.TestCase):
    def test_preserve_punctuation_without_moving_provider_word_times(self):
        events = [{"text": "先走", "start": 0.2, "end": 0.5}, {"text": "再停", "start": 0.8, "end": 1.2}]
        restored = worker.restore_punctuation(events, "先走，再停。")
        self.assertEqual([e["text"] for e in restored], ["先走，", "再停。"])
        self.assertEqual(restored[1]["start"], 0.8)
        self.assertEqual(len(worker.caption_groups(restored)), 2)
        self.assertEqual(worker.restore_punctuation(events, "不同内容。"), events)

    def test_actions_use_actual_words_and_reject_overlap(self):
        words = [{"text": "滑动", "start": 2.3, "end": 2.8}, {"text": "停下", "start": 4.7, "end": 5.2}]
        beat = {"id": "b1", "narration": "滑动，停下。", "states": [[], [], []],
                "moveCues": [{"phrase": "滑动"}, {"phrase": "停下"}]}
        self.assertEqual(worker.action_times(beat, words, 7), [2.3, 4.7])
        beat["moveCues"][1] = {"phrase": "滑动", "delay": 0.2}
        with self.assertRaisesRegex(ValueError, "Overlapping"):
            worker.action_times(beat, words, 7)

    def test_full_pcm_assembly_has_no_accumulating_frame_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            audio = root / "source.wav"
            samples = 49873
            with wave.open(str(audio), "wb") as target:
                target.setparams((1, 2, 48000, 0, "NONE", "uncompressed"))
                target.writeframes(b"\1\0" * samples)
            speech = {"samples": samples, "audio": str(audio), "cacheKey": "fake",
                      "wordBoundaries": [{"text": "测试", "start": 0.1, "end": 0.9}]}
            calls = []
            async def synth(*args, **kwargs):
                calls.append(args[0]["id"])
                return speech
            plan = {"fps": 30, "voice": {}, "beats": [{"id": f"b{i}", "narration": "测试。"} for i in range(51)]}
            plan_path = root / "plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            with patch.object(worker, "synthesize_one", synth):
                asyncio.run(worker.produce(plan_path, root / "out", "ffmpeg", True))
            self.assertEqual(len(calls), 1, "Repeated narration must share the cache writer")
            timeline = json.loads((root / "out/timeline.json").read_text(encoding="utf-8"))
            with wave.open(str(root / "out/narration.wav"), "rb") as result:
                self.assertEqual(result.getnframes(), timeline["totalFrames"] * 1600)
                self.assertEqual(result.getnframes() / 48000, timeline["durationSeconds"])
            for previous, following in zip(timeline["beats"], timeline["beats"][1:]):
                self.assertEqual(previous["startFrame"] + previous["frames"], following["startFrame"])


if __name__ == "__main__":
    unittest.main()
