"""Regression tests for the per-shot Pipa renderer. GPL-3.0-only."""
import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


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


class RetryLayoutTest(unittest.TestCase):
    def test_image_replacement_preserves_the_source_clip_and_reference_order(self):
        shot = {
            'id': 'S48',
            'cast': ['A', 'B'],
            'images': ['navy', 'red', 'seated'],
            'motion': 'same-source-shot',
        }
        with TemporaryDirectory(prefix='pipa-retry-layout-') as directory:
            root = Path(directory)
            def mock_upload(api, run, name):
                return {'file_id': name}

            with patch.object(worker, 'uploaded', side_effect=mock_upload), patch.object(worker.video, 'submit'):
                for number, overrides, expected_images, expected_motion in (
                    (2, {}, ['navy', 'red', 'seated', 'kneeling', 'wide'], 'same-source-shot'),
                    (3, {'replacePreparedLayouts': True}, ['navy', 'red', 'kneeling', 'wide'], 'same-source-shot'),
                    (4, {'replaceAllImages': True}, ['kneeling', 'wide'], 'same-source-shot'),
                    (5, {'motionGuide': 'masked-source-shot'}, ['navy', 'red', 'seated', 'kneeling', 'wide'],
                     'masked-source-shot'),
                ):
                    attempt = root / f'attempt-{number:03}'
                    attempt.mkdir()
                    worker.video.save(attempt / 'retry.json', {
                        'prompt': 'Same original motion and cast',
                        'seed': 1235,
                        'additionalImages': ['kneeling', 'wide'],
                        **overrides,
                    })
                    worker.post(None, root, shot, attempt)
                    request = worker.video.read(attempt / 'request.json')
                    self.assertEqual(expected_images, [item['file_id'] for item in request['image_reference']])
                    self.assertEqual([{'file_id': expected_motion}], request['video_reference'])


class RenderSelectionTest(unittest.TestCase):
    def test_scheduled_calibration_keeps_requested_order_and_skips_final_assembly(self):
        plan = {
            'schemaVersion': 'vivhite-shotwise-prepared-1',
            'plan': {},
            'episode': {},
            'shots': [{'id': 'S01'}, {'id': 'S05'}, {'id': 'S11'}],
        }
        with TemporaryDirectory(prefix='pipa-shot-selection-') as directory:
            arguments = ['render-shotwise.py', '--directory', directory, 'render',
                         '--scheduled', '--shot', 'S11', '--shot', 'S01']
            with (patch.object(sys, 'argv', arguments), patch.object(worker.video, 'read', return_value=plan),
                  patch.object(worker, 'check_asset'), patch.object(worker, 'run_scheduled') as scheduled):
                worker.main()

            selected = {**plan, 'shots': [{'id': 'S11'}, {'id': 'S01'}]}
            scheduled.assert_called_once_with(worker.video.DEFAULT_API, Path(directory).resolve(),
                                              selected, assemble=False)


if __name__ == '__main__':
    unittest.main()
