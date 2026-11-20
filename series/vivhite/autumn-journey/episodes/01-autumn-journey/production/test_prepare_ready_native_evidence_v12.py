"""Regression checks for local preparation ordering and immutable source bindings."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('ready_native_evidence', Path(__file__).with_name('prepare-ready-native-evidence-v12.py'))
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


class ReadyEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        for name in ['jobs', 'sources', 'clip-inspection']:
            (self.directory / name).mkdir()

    def save(self, path, data):
        path.write_text(json.dumps(data), encoding='utf-8')

    def fixture(self, identity, completed, frames=120):
        source = self.directory / 'sources' / (identity + '.mp4')
        source.write_bytes(b'unit-fixture-not-a-real-or-approved-video')
        digest = worker.sha(source)
        job = {'jobId': 'job-' + identity, 'planSha256': worker.PLAN_SHA,
            'status': 'completed' if completed else 'queued', 'sourceSha256': digest}
        self.save(self.directory / 'jobs' / (identity + '.json'), job)
        report = {'status': 'decoded', 'shotId': identity, 'decodedFrames': frames,
            'usedFramesAnalysed': frames, 'identity': {'sourceSha256': digest}}
        self.save(self.directory / 'clip-inspection' / (identity + '.json'), report)
        return source

    def test_later_completed_ending_is_not_blocked_by_earlier_queued_shot(self):
        self.fixture('S42', False)
        self.fixture('S48', True, 336)
        ready = worker.ready_batch(self.directory, ['S42', 'S48'], {'S42': 'job-S42', 'S48': 'job-S48'})
        self.assertEqual([row[0] for row in ready], ['S48'])
        self.assertFalse((self.directory / 'preparation.json').exists())

    def test_submitted_job_binding_change_is_rejected(self):
        self.fixture('S42', True)
        with self.assertRaisesRegex(ValueError, 'job binding changed'):
            worker.ready_source(self.directory, 'S42', 'different-job', 120)

    def test_missing_report_waits_but_changed_source_is_rejected(self):
        source = self.fixture('S48', True, 336)
        report = self.directory / 'clip-inspection/S48.json'
        content = report.read_bytes()
        report.unlink()
        self.assertIsNone(worker.ready_source(self.directory, 'S48', 'job-S48', 336))
        report.write_bytes(content)
        source.write_bytes(b'changed-unreviewed-fixture')
        with self.assertRaisesRegex(ValueError, 'stale local source inspection'):
            worker.ready_source(self.directory, 'S48', 'job-S48', 336)


if __name__ == '__main__':
    unittest.main()
