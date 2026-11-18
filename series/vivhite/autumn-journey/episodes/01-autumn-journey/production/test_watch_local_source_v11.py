"""Local event-watcher recovery and bounded-error behavior. GPL-3.0-only."""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('local_source_watch', Path(__file__).with_name('watch-local-source-v11.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class LocalSourceWatchTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.watcher = module.LocalSourceWatch(self.directory, 'S16')
        self.utc = datetime(2026, 11, 19, tzinfo=timezone.utc)

    def snapshot(self, status, at=None):
        (self.directory/'controller.json').write_text(json.dumps({
            'status': status, 'snapshotAt': (at or self.utc).isoformat()}), encoding='utf-8')

    def test_fresh_restart_then_active_does_not_raise_false_attention(self):
        for offset, status in [(0, 'watching-active-worker'), (20, 'started-generation'),
                               (40, 'watching-active-worker')]:
            self.snapshot(status, self.utc+timedelta(seconds=offset))
            self.assertIsNone(self.watcher.tick(self.utc+timedelta(seconds=offset), offset))

    def test_fresh_retry_heartbeat_does_not_hide_stuck_transition(self):
        self.snapshot('waiting-for-client-retry-backoff')
        self.assertIsNone(self.watcher.tick(self.utc, 0))
        self.snapshot('waiting-for-client-retry-backoff', self.utc+timedelta(seconds=361))
        result = self.watcher.tick(self.utc+timedelta(seconds=361), 361)
        self.assertEqual('client-transition-exceeded-grace', result['reason'])

    def test_unreadable_journals_have_deadline_and_recovery_resets_it(self):
        self.assertIsNone(self.watcher.tick(self.utc, 0))
        self.assertEqual('local-journal-unreadable', self.watcher.tick(self.utc, 181)['reason'])
        self.snapshot('watching-active-worker')
        self.assertIsNone(self.watcher.tick(self.utc, 182))
        (self.directory/'controller.json').write_text('{broken', encoding='utf-8')
        self.assertIsNone(self.watcher.tick(self.utc, 183))

    def test_matching_finished_source_is_ready_even_after_controller_completion(self):
        self.snapshot('complete-technical-preview-awaiting-semantic-review')
        (self.directory/'jobs').mkdir()
        (self.directory/'clip-inspection').mkdir()
        digest = 'a'*64
        job = {'status': 'completed', 'jobId': 'existing-job', 'sourceSha256': digest}
        report = {'status': 'decoded', 'identity': {'sourceSha256': digest},
                  'decodedFrames': 120, 'usedFramesAnalysed': 120}
        (self.directory/'jobs/S16.json').write_text(json.dumps(job), encoding='utf-8')
        (self.directory/'clip-inspection/S16.json').write_text(json.dumps(report), encoding='utf-8')
        self.assertEqual('source-ready', self.watcher.tick(self.utc, 0)['event'])
        report['identity']['sourceSha256'] = 'b'*64
        (self.directory/'clip-inspection/S16.json').write_text(json.dumps(report), encoding='utf-8')
        self.assertEqual('attention', self.watcher.tick(self.utc, 1)['event'])

    def test_real_attention_and_stale_heartbeat_still_alert(self):
        self.snapshot('attention-required')
        self.assertEqual('controller-status', self.watcher.tick(self.utc, 0)['reason'])
        self.snapshot('watching-active-worker', self.utc-timedelta(seconds=181))
        self.assertEqual('controller-heartbeat-age', self.watcher.tick(self.utc, 1)['reason'])


if __name__ == '__main__':
    unittest.main()
