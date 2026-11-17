"""Check local slowdown preserves the rest of the real-time shot and its frames."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from retime_local_region import retime_region


class LocalRegionRetimeTest(unittest.TestCase):
    def test_invalid_parameters_fail_before_opening_source(self):
        for factor in (1, 33, float('nan')):
            with self.subTest(factor=factor), self.assertRaises(ValueError):
                retime_region('missing.mp4', 'separate.mp4', (0, 0, 48, 48), factor, .5, 14, 4, 'test')
        with self.assertRaises(ValueError):
            retime_region('missing.mp4', 'separate.mp4', (0, 0, 3, 48), 14, .5, 14, 4, 'test')

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
    def test_fourteen_second_region_slowdown_keeps_surrounding_motion_at_original_time(self):
        with tempfile.TemporaryDirectory(prefix='vivhite-region-retime-') as temporary:
            root = Path(temporary)
            source, output = root / 'source.mp4', root / 'candidate.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=s=160x96:r=24:d=14',
                            '-frames:v', '336', '-c:v', 'libx264', str(source)], check=True)
            original = source.read_bytes()
            receipt = retime_region(source, output, (96, 32, 144, 80), 14, .5, 14, 4, 'Unit region slowdown', motion_fps=12)
            self.assertEqual(receipt['identity']['frames'], 336)
            self.assertEqual(receipt['identity']['motionSampleFps'], 12)
            self.assertEqual(receipt['regionSourceIntervalSeconds'], [.5, 1.5])
            self.assertFalse(receipt['loopOrClonedPaddingUsed'])
            self.assertFalse(receipt['entersFilm'])
            self.assertEqual(receipt['semanticReview'], 'pending')
            self.assertEqual(source.read_bytes(), original)
            captures = [cv2.VideoCapture(str(p)) for p in (source, output)]
            outside_errors, inside_errors = [], []
            count = 0
            try:
                while True:
                    a, frame_a = captures[0].read()
                    b, frame_b = captures[1].read()
                    self.assertEqual(a, b)
                    if not a:
                        break
                    delta = frame_a.astype(np.float32) - frame_b.astype(np.float32)
                    outside_errors.append(float(np.mean(delta[:, :80] ** 2)))
                    inside_errors.append(float(np.mean(delta[40:72, 104:136] ** 2)))
                    count += 1
            finally:
                for capture in captures:
                    capture.release()
            self.assertEqual(count, 336)
            self.assertLess(max(outside_errors), 25)
            self.assertGreater(np.mean(inside_errors), np.mean(outside_errors) * 5)
            with self.assertRaisesRegex(ValueError, 'interpolation context'):
                retime_region(source, root / 'invalid-tail.mp4', (96, 32, 144, 80), 14, 13.5, 14, 4, 'Invalid tail')
            self.assertFalse((root / 'invalid-tail.mp4').exists())


if __name__ == '__main__':
    unittest.main()
