"""Verify an explicit source interval cannot silently use the rejected opening."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1]))
from retime_local_clip import retime


class RetimeIntervalTest(unittest.TestCase):
    def test_invalid_interval_values_fail_before_reading_source(self):
        for value in (-1, float('nan'), float('inf')):
            with self.subTest(start=value), self.assertRaises(ValueError):
                retime(Path('missing.mp4'), Path('separate.mp4'), 4, 'inspection', value)
        for value in (float('nan'), float('inf')):
            with self.subTest(factor=value), self.assertRaises(ValueError):
                retime(Path('missing.mp4'), Path('separate.mp4'), value, 'inspection')

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
    def test_candidate_starts_inside_requested_later_interval(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source, output = directory / 'original.mp4', directory / 'later.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                            'color=red:s=128x64:r=24:d=2', '-f', 'lavfi', '-i',
                            'color=blue:s=128x64:r=24:d=4', '-filter_complex',
                            '[0:v][1:v]concat=n=2:v=1:a=0[v]', '-map', '[v]',
                            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(source)], check=True)
            original_bytes = source.read_bytes()
            receipt = retime(source, output, 4, 'Use later stable blue interval', 2.5)
            self.assertEqual(receipt['sourceIntervalSeconds'], [2.5, 3.75])
            self.assertEqual(receipt['identity']['startSeconds'], 2.5)
            self.assertEqual(source.read_bytes(), original_bytes)
            self.assertEqual(receipt['semanticReview'], 'pending')
            self.assertFalse(receipt['entersFilm'])
            frame = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(output),
                                             '-frames:v', '1', '-f', 'rawvideo',
                                             '-pix_fmt', 'rgb24', '-'])
            red, green, blue = frame[:3]
            self.assertGreater(blue, 240)
            self.assertLess(red, 15)
            self.assertLess(green, 15)
            self.assertEqual(retime(source, output, 4, 'Same reviewed candidate', 2.5)['sha256'],
                             receipt['sha256'])


if __name__ == '__main__':
    unittest.main()
