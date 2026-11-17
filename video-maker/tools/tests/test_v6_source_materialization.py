"""Transfer guards use explicit unit fixtures, never real semantic approvals."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
from reference_finisher import sha, write_json

SCRIPT = (Path(__file__).parents[3] / 'series/vivhite/autumn-journey/episodes/'
          '01-autumn-journey/production/materialize-sources-v6.py')
SPEC = importlib.util.spec_from_file_location('v6_sources', SCRIPT)
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


class SourceMaterializationTest(unittest.TestCase):
    def fixture(self, directory):
        episode, base = directory / 'episode', directory / 'media'
        episode.mkdir()
        origin = base / 'long-source'
        (origin / 'sources').mkdir(parents=True)
        (origin / 'clip-inspection').mkdir()
        (origin / 'jobs').mkdir()
        source = origin / 'sources/S20.mp4'
        source.write_bytes(b'unit fixture source, not a playable or approved video')
        evidence = directory / 'frames.png'
        evidence.write_bytes(b'unit fixture evidence, not an actual image')
        plan = {'schemaVersion': 'vivhite-local-two-stage-video-1', 'stage': 'draft',
                'model': 'fasth3-omni-bf16', 'width': 1344, 'height': 768,
                'fps': 30, 'sourceFps': 24, 'maxShotSeconds': 5,
                'shotDurationExceptions': {'S20': 10}, 'totalFrames': 300,
                **{key: True for key in ('noSpeech', 'noHumanFaces', 'noAddedPeople', 'allCharactersFemale')},
                'shots': [{'id': 'S20', 'seconds': 10, 'sourceSeconds': 10,
                           'startFrame': 0, 'prompt': 'Unit fixture.'}]}
        write_json(episode / 'production-plan-v6-bf16-768p.json', plan)
        original = copy.deepcopy(plan)
        original['revision'] = 'original unit fixture'
        write_json(episode / 'long.json', original)
        row = {'id': 'S20', 'sourceSha256': sha(source), 'method': 'assistant-frame-review',
               'reviewedAt': 'unit-fixture-time', 'allSourceFrameReview': True,
               'allUsedFrameReview': True, 'reviewedNativeFrames': 240,
               'frameEvidence': [{'path': str(evidence), 'sha256': sha(evidence), 'items': 240}],
               **{key: 'passed' for key in worker.CHECKS}}
        write_json(origin / 'clip-decisions.json', {'sourcePlanSha256': sha(episode / 'long.json'), 'shots': [row]})
        write_json(origin / 'clip-inspection/S20.json', {
            'identity': {'sourceSha256': sha(source)}, 'usedFramesAnalysed': 240})
        write_json(origin / 'jobs/S20.json', {'jobId': 'fixture-original-job'})
        return episode, base, origin, source, evidence

    def test_exact_bytes_and_original_review_time_are_preserved_in_separate_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            episode, base, origin, source, _ = self.fixture(directory)
            target = base / 'new-assembly'
            digest = sha(source)
            with patch.object(worker, 'EP', episode), patch.object(worker, 'ORIGINS', {'S20': ('long-source', 'long.json')}):
                worker.materialize(base, target)
                self.assertEqual(sha(source), digest)
                self.assertEqual(sha(target / 'sources/S20.mp4'), digest)
                row = json.loads((target / 'clip-decisions.json').read_text())['shots'][0]
                self.assertEqual(row['reviewedAt'], 'unit-fixture-time')
                self.assertEqual(row['reviewedNativeFrames'], 240)
                imported = json.loads((target / 'source-imports.json').read_text())
                self.assertEqual(imported['shots'][0]['originJobReceipt']['jobId'], 'fixture-original-job')
                with self.assertRaisesRegex(ValueError, 'existing run'):
                    worker.materialize(base, target)
                self.assertEqual(sha(target / 'sources/S20.mp4'), digest)

    def test_stale_or_incomplete_or_rejected_inputs_never_create_an_assembly(self):
        for failure in ('short-review', 'failed-eyes', 'changed-evidence', 'changed-source'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                episode, base, origin, source, evidence = self.fixture(directory)
                decisions = json.loads((origin / 'clip-decisions.json').read_text())
                if failure == 'short-review':
                    decisions['shots'][0]['reviewedNativeFrames'] = 120
                elif failure == 'failed-eyes':
                    decisions['shots'][0]['referenceAppearance'] = 'failed'
                elif failure == 'changed-evidence':
                    evidence.write_bytes(b'changed evidence')
                else:
                    source.write_bytes(b'changed source')
                write_json(origin / 'clip-decisions.json', decisions)
                target = base / 'new-assembly'
                with patch.object(worker, 'EP', episode), patch.object(worker, 'ORIGINS', {'S20': ('long-source', 'long.json')}):
                    with self.assertRaises(ValueError):
                        worker.materialize(base, target)
                self.assertFalse(target.exists())

    def test_imported_source_keeps_its_real_job_instead_of_a_new_rejected_attempt(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary)
            episode,base,origin,source,_=self.fixture(directory)
            write_json(origin/'generation-plan.json',{'origin':'real earlier generation'})
            write_json(origin/'generation-job.json',{'jobId':'real-earlier-job',
                'planSha256':sha(origin/'generation-plan.json')})
            write_json(origin/'processing.json',{'scope':'Unit fixture, no semantic approval'})
            write_json(origin/'source-selections.json',{'selections':{'S20':{
                'path':'sources/S20.mp4','sha256':sha(source),'parent':'sources/S20.mp4',
                'parentSha256':sha(source),'receipt':'processing.json',
                'generationJobReceipt':'generation-job.json','generationPlan':'generation-plan.json'}}})
            with patch.object(worker,'EP',episode),patch.object(worker,'ORIGINS',{'S20':('long-source','long.json')}):
                target=base/'first-assembly'
                worker.materialize(base,target)
                imported=json.loads((target/'source-imports.json').read_text())
                self.assertEqual(imported['shots'][0]['originJobReceipt']['jobId'],'real-earlier-job')
                write_json(origin/'generation-plan.json',{'origin':'changed'})
                with self.assertRaisesRegex(ValueError,'generation plan'):
                    worker.materialize(base,base/'must-not-exist')
                self.assertFalse((base/'must-not-exist').exists())


if __name__ == '__main__':
    unittest.main()
