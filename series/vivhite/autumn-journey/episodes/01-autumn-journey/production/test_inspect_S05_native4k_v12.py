"""Exercise repair provenance gates with disposable fixtures, never real approvals."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

FILE = Path(__file__).with_name('inspect-S05-native4k-v12.py')
SPEC = importlib.util.spec_from_file_location('saddle_native4k_inspection', FILE)
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


class RepairProvenanceTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name) / worker.RUN_NAME
        for name in ('jobs', 'requests', 'input-sources', 'sources-raw', 'sources', 'clip-inspection'):
            (self.directory / name).mkdir(parents=True, exist_ok=True)
        self.input = self.directory / 'input-sources/S05.mp4'
        self.source = self.directory / 'sources/S05.mp4'
        self.raw = self.directory / 'sources-raw/S05.mp4'
        # Byte-only provenance fixtures. No playable media or semantic decisions.
        self.input.write_bytes(b'repaired draft fixture')
        self.source.write_bytes(b'normalized native fixture')
        self.raw.write_bytes(b'original server fixture')
        self.plan = copy.deepcopy(worker.read(worker.PLAN))
        self.plan['shots'][0]['inputSourceSha256'] = worker.sha(self.input)
        self.plan_file = self.directory / 'plan.json'
        self.save(self.plan_file, self.plan)
        self.addCleanup(patch.stopall)
        patch.object(worker, 'PLAN', self.plan_file).start()
        patch.object(worker, 'PLAN_SHA', worker.sha(self.plan_file)).start()
        patch.object(worker, 'INPUT_SHA', worker.sha(self.input)).start()
        self.request_file = self.directory / 'requests/S05.json'
        self.request = {'model': 'open-h3-2k', 'size': '3840x2160', 'sampler': 'up3',
                        'seed': 1234, 'prompt': self.plan['shots'][0]['prompt']}
        self.save(self.request_file, self.request)
        self.job = {'status': 'completed', 'shotId': 'S05', 'jobId': worker.JOB_ID,
            'planSha256': worker.PLAN_SHA, 'requestSha256': worker.sha(self.request_file),
            'sourceFile': 'sources/S05.mp4', 'sourceSha256': worker.sha(self.source),
            'rawFile': 'sources-raw/S05.mp4', 'rawSha256': worker.sha(self.raw),
            'remote': {'id': worker.JOB_ID, 'status': 'completed', 'model': 'open-h3-2k',
                'size': '3840x2160', 'result': {'width': 3840, 'height': 2160, 'frames': 120,
                    'fps': 24, 'windows': 1, 'native_resolution': '4k', 'sha256': worker.sha(self.raw)}}}
        self.report = {'status': 'decoded', 'shotId': 'S05', 'sourceFps': 24,
            'decodedFrames': 120, 'usedFramesAnalysed': 120,
            'identity': {'sourceSha256': worker.sha(self.source), 'usedSeconds': 5},
            'allUsedFrameEvidence': [{'items': 120}]}
        self.flush()

    @staticmethod
    def save(path, value):
        path.write_text(json.dumps(value), encoding='utf-8')

    def flush(self):
        self.save(self.directory / 'jobs/S05.json', self.job)
        self.save(self.directory / 'clip-inspection/S05.json', self.report)

    def test_complete_provenance_returns_source_without_creating_approval(self):
        source, _, _, _, _ = worker.bound_source(self.directory)
        self.assertEqual(source, self.source)
        self.assertFalse((self.directory / 'clip-decisions.json').exists())

    def test_queued_job_does_not_create_images_or_acceptance(self):
        self.job['status'] = 'queued'
        self.flush()
        with self.assertRaisesRegex(ValueError, 'has not completed'):
            worker.bound_source(self.directory)
        self.assertFalse((self.directory / 'clip-decisions.json').exists())

    def test_old_job_and_changed_source_or_input_are_rejected(self):
        original = copy.deepcopy(self.job)
        for field, value in [('jobId', 'old-missing-saddle-job'), ('planSha256', 'old-plan'),
                             ('sourceSha256', 'old-native-source')]:
            with self.subTest(field=field):
                self.job = copy.deepcopy(original)
                self.job[field] = value
                self.flush()
                with self.assertRaises(ValueError):
                    worker.bound_source(self.directory)
        self.job = original
        self.flush()
        self.input.write_bytes(b'old missing saddle draft')
        with self.assertRaisesRegex(ValueError, 'input'):
            worker.bound_source(self.directory)

    def test_request_hash_and_native_specifications_are_required(self):
        original = copy.deepcopy(self.job)
        for field, value in [('width', 2560), ('height', 1440), ('windows', 3),
                             ('frames', 124), ('fps', 30), ('native_resolution', '2k')]:
            with self.subTest(field=field):
                self.job = copy.deepcopy(original)
                self.job['remote']['result'][field] = value
                self.flush()
                with self.assertRaisesRegex(ValueError, 'single-window native UHD'):
                    worker.bound_source(self.directory)
        self.job = original
        self.flush()
        self.request['size'] = '2560x1440'
        self.save(self.request_file, self.request)
        with self.assertRaisesRegex(ValueError, 'Request'):
            worker.bound_source(self.directory)
        self.job['requestSha256'] = worker.sha(self.request_file)
        self.flush()
        with self.assertRaisesRegex(ValueError, 'Request'):
            worker.bound_source(self.directory)

    def test_incomplete_report_and_changed_raw_download_are_rejected(self):
        self.report['allUsedFrameEvidence'][0]['items'] = 96
        self.flush()
        with self.assertRaisesRegex(ValueError, 'complete120-frame'):
            worker.bound_source(self.directory)
        self.report['allUsedFrameEvidence'][0]['items'] = 120
        self.flush()
        self.raw.write_bytes(b'changed server download')
        with self.assertRaisesRegex(ValueError, 'downloads'):
            worker.bound_source(self.directory)

    def test_origin_path_cannot_escape_the_separate_repair_run(self):
        self.job['sourceFile'] = '../old-S05.mp4'
        self.flush()
        with self.assertRaisesRegex(ValueError, 'stay inside'):
            worker.bound_source(self.directory)


if __name__ == '__main__':
    unittest.main()
