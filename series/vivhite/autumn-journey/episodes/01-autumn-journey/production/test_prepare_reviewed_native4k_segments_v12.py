"""Regression checks for revoked-source cache exclusion and retained failures."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('reviewed_segment_cache',
    Path(__file__).with_name('prepare-reviewed-native4k-segments-v12.py'))
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


class ReviewedSegmentCacheTests(unittest.TestCase):
    def test_revoked_raw_source_cannot_create_cache_or_reach_source_fallback(self):
        shot = {'id': 'S05', 'seconds': 5, 'sourceSeconds': 5}
        decision = {'id': 'S05', 'decision': 'rejected'}
        with tempfile.TemporaryDirectory() as temporary:
            directory, cache = Path(temporary) / 'origin', Path(temporary) / 'cache'

            def read(path):
                if path.name == 'production-plan-v11-native-4k.json':
                    return {'shots': [shot]}
                return {'sourcePlanSha256': worker.PLAN_SHA, 'shots': [decision]}

            with patch.object(worker, 'sha', return_value=worker.PLAN_SHA), \
                    patch.object(worker, 'read', side_effect=read), \
                    patch.object(worker, 'selected_source') as fallback:
                with self.assertRaisesRegex(ValueError, 'accepted-source review required: S05'):
                    worker.prepare(directory, cache, ['S05'])
                fallback.assert_not_called()
            self.assertFalse(cache.exists())

    def test_accepted_flag_cannot_reuse_inspection_for_different_source_bytes(self):
        digest = 'a' * 64
        shot = {'id': 'S38', 'seconds': 4, 'sourceSeconds': 5}
        decision = dict(id='S38', decision='accepted', method='assistant-frame-review',
                        allSourceFrameReview=True, allUsedFrameReview=True,
                        reviewedNativeFrames=120, sourceSha256=digest)
        decision.update({key: 'passed' for key in worker.CHECKS})

        def read(path):
            if path.name == 'clip-decisions.json':
                return {'sourcePlanSha256': worker.PLAN_SHA, 'shots': [decision]}
            if path.name == 'S38.json':
                return {'status': 'completed', 'planSha256': worker.PLAN_SHA, 'sourceSha256': digest}
            return {'identity': {'sourceSha256': 'b' * 64}, 'decodedFrames': 120, 'usedFramesAnalysed': 120}

        with patch.object(worker, 'read', side_effect=read), \
                patch.object(worker, 'sha', return_value=digest), \
                patch.object(worker, 'selected_source', return_value=(Path('source.mp4'), Path('report.json'))), \
                patch.object(worker, 'contained', return_value=Path('source.mp4')):
            with self.assertRaisesRegex(ValueError, 'Stale source, decision, job or inspection: S38'):
                worker.accepted_source(Path('origin'), shot)

    def test_encoder_failure_keeps_partial_and_failed_state_without_valid_receipt(self):
        shot = {'id': 'S38', 'seconds': 4, 'sourceSeconds': 5}
        digest = 'a' * 64
        with tempfile.TemporaryDirectory() as temporary:
            directory, cache = Path(temporary) / 'origin', Path(temporary) / 'cache'

            def read(path):
                return {'shots': [shot]} if path.name.endswith('native-4k.json') else {'toolDirectories': []}

            def fail(argv, **kwargs):
                Path(argv[-1]).write_bytes(b'partial encoder output')
                raise subprocess.CalledProcessError(1, argv)

            with patch.object(worker, 'read', side_effect=read), \
                    patch.object(worker, 'sha', side_effect=lambda path: worker.PLAN_SHA
                                 if Path(path).name.endswith('native-4k.json') else digest), \
                    patch.object(worker, 'accepted_source', return_value=(Path('source.mp4'), digest)), \
                    patch.object(worker, 'probe', return_value=(3840, 2160, '24/1', 120)), \
                    patch.object(worker.subprocess, 'run', side_effect=fail), patch.dict(worker.os.environ):
                with self.assertRaises(subprocess.CalledProcessError):
                    worker.prepare(directory, cache, ['S38'])
            self.assertEqual((cache / 'S38.partial.mp4').read_bytes(), b'partial encoder output')
            self.assertTrue((cache / 'S38.encoder.log').exists())
            self.assertFalse((cache / 'S38.mp4').exists())
            self.assertFalse((cache / 'S38.json').exists())
            state = json.loads((cache / 'cache-preparation.json').read_text(encoding='utf-8'))
            self.assertEqual(state['status'], 'failed-partials-retained')
            self.assertFalse(state['semanticAcceptance'])


if __name__ == '__main__':
    unittest.main()
