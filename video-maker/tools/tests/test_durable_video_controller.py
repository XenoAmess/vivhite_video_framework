"""Offline recovery policy checks, without server calls or semantic approvals.

GPL-3.0-only.
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).parents[1]))
import durable_video_controller as worker


class DurableRecoveryTest(unittest.TestCase):
    def test_network_disconnect_resumes_a_known_task(self):
        self.assertTrue(worker.can_resume({'status':'interrupted-or-failed',
            'error':'<urlopen error [WinError 10054] Connection reset>'},
            [{'status':'in_progress','jobId':'known-server-id'}]))
        self.assertTrue(worker.can_resume({'status':'generating'},[{'status':'download_pending'}]))

    def test_ambiguous_post_and_remote_terminal_failure_do_not_duplicate(self):
        for state in ('submitting','submission-uncertain','failed','cancelled'):
            with self.subTest(state=state):
                self.assertFalse(worker.can_resume({'status':'generating'},[{'status':state}]))

    def test_content_binding_and_native_media_errors_require_inspection(self):
        for error in ('Native dimensions differ','HTTP 422: invalid input',
                      'Character review blocked','CUDA out of memory'):
            with self.subTest(error=error):
                self.assertFalse(worker.can_resume({'status':'interrupted-or-failed','error':error},[]))
        self.assertFalse(worker.can_resume({'status':'sources-completed-semantic-review-pending'},[]))

    def test_all_downloads_do_not_complete_before_last_full_inspection(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            plan = directory/'plan.json'
            plan.write_text(json.dumps({'shots':[{'id':'S01','sourceSeconds':5}]}),encoding='utf-8')
            config = {'directory':str(directory),'plan':str(plan)}
            jobs = [{'shotId':'S01','status':'completed','sourceSha256':'actual-source'}]
            self.assertFalse(worker.sources_complete(config,jobs))
            report = directory/'clip-inspection/S01.json'
            report.parent.mkdir()
            report.write_text(json.dumps({'status':'decoded','identity':{'sourceSha256':'actual-source'},
                'decodedFrames':119}),encoding='utf-8')
            self.assertFalse(worker.sources_complete(config,jobs))
            report.write_text(json.dumps({'status':'decoded','identity':{'sourceSha256':'actual-source'},
                'decodedFrames':120}),encoding='utf-8')
            self.assertTrue(worker.sources_complete(config,jobs))

    def test_changed_frozen_worker_or_plan_blocks_restart(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'frozen.py'
            path.write_text('version 1',encoding='utf-8')
            config = {'plan':str(path),'planSha256':worker.sha(path),
                'frozenWorkers':[{'path':str(path),'sha256':worker.sha(path)}]}
            worker.verify_frozen(config)
            path.write_text('changed',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'plan changed'):
                worker.verify_frozen(config)


if __name__ == '__main__':
    unittest.main()
