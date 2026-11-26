"""Regression tests for the per-shot Pipa renderer. GPL-3.0-only."""
import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[5] / 'video-maker' / 'tools'))
SPEC = importlib.util.spec_from_file_location('pipa_shotwise', HERE / 'render-shotwise.py')
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


def picture_digests(source):
    output = worker.ff('-xerror', '-i', source, '-an', '-fps_mode', 'passthrough', '-f', 'framemd5', '-')
    return [line.rsplit(',', 1)[-1].strip() for line in output.splitlines() if not line.startswith('#')]


class PictureClockTest(unittest.TestCase):
    def test_concat_preserves_decoded_frames_at_exact_cut_times(self):
        with TemporaryDirectory(prefix='pipa-picture-clock-') as directory:
            root = Path(directory)
            clips = []
            expected = []
            for index, frames in enumerate((40, 24, 36, 29, 29, 28, 20, 48, 19, 21, 23, 21)):
                path = root / f'shot-{index:02}.mp4'
                worker.ff(
                    '-f', 'lavfi', '-i', 'testsrc2=size=96x54:rate=24',
                    '-vf', f'hue=h={index * 22}', '-frames:v', frames, '-an',
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                    '-video_track_timescale', worker.PICTURE_TIMESCALE, path,
                )
                clips.append((path, frames))
                expected.extend(picture_digests(path))

            concat = root / 'picture.ffconcat'
            output = root / 'joined.mp4'
            worker.write_picture_concat(concat, clips)
            worker.ff(
                '-f', 'concat', '-safe', 0, '-i', concat, '-c:v', 'copy',
                '-video_track_timescale', worker.PICTURE_TIMESCALE, output,
            )
            worker.verify_picture_clock(output, len(expected))
            self.assertEqual(338, len(expected))
            self.assertEqual(expected, picture_digests(output))


if __name__ == '__main__':
    unittest.main()
