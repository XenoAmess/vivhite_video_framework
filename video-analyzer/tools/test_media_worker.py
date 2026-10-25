"""Small real-codec integration test; no model download or mocked success artifacts."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

WORKER = Path(__file__).with_name("media_worker.py")


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg is required")
class MediaWorkerTest(unittest.TestCase):
    def test_full_decode_audio_and_configuration_cache(self):
        with tempfile.TemporaryDirectory(prefix="vivhite-media-test-") as temporary:
            root = Path(temporary)
            source = root / "source.mkv"
            subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-f", "lavfi", "-i",
                            "testsrc2=size=320x180:rate=30:duration=3", "-f", "lavfi", "-i",
                            "sine=frequency=440:sample_rate=16000:duration=3", "-c:v", "ffv1",
                            "-c:a", "pcm_s16le", str(source)], check=True, timeout=30)
            output = root / "evidence"
            command = [sys.executable, str(WORKER), "vision", "--input", str(source),
                       "--output", str(output), "--sample-seconds", "1"]
            subprocess.run(command, check=True, capture_output=True, timeout=60)
            visual = json.loads((output / "vision.json").read_text(encoding="utf-8"))
            self.assertEqual(90, visual["decodedFrames"])
            self.assertEqual(3000, visual["decodedEndMs"])
            self.assertEqual([], visual["decodeGaps"])
            self.assertEqual("not_run", visual["ocrPolicy"]["recognitionCompleteness"])
            self.assertEqual([0, 1000, 2000], [frame["timeMs"] for frame in visual["frames"]])
            cached = subprocess.run(command, check=True, capture_output=True, text=True, timeout=30)
            self.assertIn("Reusing completed", cached.stdout)
            command[-1] = "0.5"
            subprocess.run(command, check=True, capture_output=True, timeout=60)
            changed = json.loads((output / "vision.json").read_text(encoding="utf-8"))
            self.assertEqual(6, len(changed["frames"]))
            subprocess.run([sys.executable, str(WORKER), "audio", "--input", str(source),
                            "--output", str(output)], check=True, capture_output=True, timeout=30)
            audio = json.loads((output / "audio-metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(3000, audio["durationMs"])
            self.assertEqual(3, len(audio["bins"]))
            self.assertTrue(all(-30 < part["rmsDbfs"] < -15 for part in audio["bins"]))


if __name__ == "__main__":
    unittest.main()
