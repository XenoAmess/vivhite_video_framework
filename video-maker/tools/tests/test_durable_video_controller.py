"""Offline recovery policy checks, without server calls or semantic approvals.

GPL-3.0-only.
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).parents[1]))
import durable_video_controller as worker


class DurableRecoveryTest(unittest.TestCase):
    def make_single_shot(self, directory):
        plan = directory/'plan.json'
        worker.save(plan,{'shots':[{'id':'S05','sourceSeconds':5,'inputSourceSha256':'input-S05'}]})
        source = directory/'sources/S05.mp4'
        source.parent.mkdir()
        source.write_bytes(b'Identity fixture only, not a video or semantic approval')
        report = directory/'clip-inspection/S05.json'
        worker.save(report,{'status':'decoded','sourceFps':24,
            'identity':{'sourceSha256':worker.sha(source),'usedSeconds':5},
            'decodedFrames':120,'usedFramesAnalysed':120,
            'allUsedFrameEvidence':[{'items':120}]})
        config = {'directory':str(directory),'plan':str(plan),'generationOnly':True}
        jobs = [{'shotId':'S05','status':'completed','sourceSha256':worker.sha(source)}]
        return config,jobs,source,report

    def test_single_shot_generation_completion_requires_exact_local_source_and_all_frames(self):
        with tempfile.TemporaryDirectory() as temporary:
            config,jobs,source,report = self.make_single_shot(Path(temporary))
            self.assertTrue(worker.generation_only_complete(config,jobs))
            original = worker.read(report)
            for change in ({'usedFramesAnalysed':119},{'sourceFps':30},{'allUsedFrameEvidence':[{'items':119}]}):
                worker.save(report,{**original,**change})
                self.assertFalse(worker.generation_only_complete(config,jobs))
            worker.save(report,original)
            source.write_bytes(b'Changed completed source')
            self.assertFalse(worker.generation_only_complete(config,jobs))
            source.unlink()
            self.assertFalse(worker.generation_only_complete(config,jobs))
            self.assertFalse(worker.generation_only_complete({**config,'generationOnly':False},jobs))

    def test_generation_watchdog_requires_matching_pushed_checkpoint(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            config,jobs,source,report = self.make_single_shot(directory)
            self.assertFalse(worker.generation_checkpoint_pushed(config,jobs))
            ledger = {'pushed':True,'sources':[['S05',worker.sha(source),worker.sha(report)]]}
            worker.save(directory/'git-checkpoint.json',ledger)
            self.assertTrue(worker.generation_checkpoint_pushed(config,jobs))
            worker.save(directory/'git-checkpoint.json',{**ledger,'pushed':False})
            self.assertFalse(worker.generation_checkpoint_pushed(config,jobs))
            worker.save(directory/'git-checkpoint.json',ledger)
            worker.save(report,{**worker.read(report),'scope':'changed inspection receipt'})
            self.assertFalse(worker.generation_checkpoint_pushed(config,jobs))

    def test_subset_checkpoint_uses_shot_id_and_its_own_episode_catalog(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root,directory = base/'checkout',base/'run'
            root.mkdir();directory.mkdir();(directory/'logs').mkdir()
            config,jobs,source,report = self.make_single_shot(directory)
            episode = root/'episode'
            evidence = episode/'assets/generated/single-repair/review'
            evidence.mkdir(parents=True)
            image = evidence/'identity.fixture'
            image.write_bytes(b'Inspection identity fixture, no generated artwork')
            worker.save(report,{**worker.read(report),'allUsedFrameEvidence':[
                {'items':120,'path':str(image),'sha256':worker.sha(image)}]})
            config.update(root=str(root),episode=str(episode/'episode.json'),planSha256=worker.sha(config['plan']),
                evidenceRelativeToEpisode='assets/generated/single-repair/review',
                sourceCatalogRelativeToEpisode='production/single-repair.json')
            jobs[0].update(rawSha256='raw',requestSha256='request',jobId='known')
            result = SimpleNamespace(returncode=0,stdout=b'',stderr=b'')
            with (patch.object(worker.subprocess,'run',return_value=result),
                  patch.object(worker.subprocess,'check_output',return_value=b'unit-commit'),
                  patch.object(worker.subprocess,'CREATE_NO_WINDOW',0,create=True)):
                worker.checkpoint_sources(config,jobs)
            catalog = worker.read(episode/'production/single-repair.json')
            self.assertEqual(catalog['totalSources'],1)
            self.assertEqual(catalog['sources'][0]['inputSourceSha256'],'input-S05')
            self.assertFalse((episode/'production/source-generation-v11-4k.json').exists())
            for key,value in [('evidenceRelativeToEpisode','../outside'),
                              ('sourceCatalogRelativeToEpisode','../outside.json')]:
                with self.subTest(key=key), self.assertRaisesRegex(ValueError,'episode directories'):
                    worker.checkpoint_sources({**config,key:value},jobs)
            with self.assertRaisesRegex(ValueError,'absent'):
                worker.checkpoint_sources(config,[{**jobs[0],'shotId':'S09'}])

    def test_network_disconnect_resumes_a_known_task(self):
        self.assertTrue(worker.can_resume({'status':'interrupted-or-failed',
            'error':'<urlopen error [WinError 10054] Connection reset>'},
            [{'status':'in_progress','jobId':'known-server-id'}]))
        self.assertTrue(worker.can_resume({'status':'generating'},[{'status':'download_pending'}]))

    def test_ambiguous_post_and_remote_terminal_failure_do_not_duplicate(self):
        for state in ('submitting','submission-uncertain','failed','cancelled'):
            with self.subTest(state=state):
                self.assertFalse(worker.can_resume({'status':'generating'},[{'status':state}]))

    def test_local_atomic_json_sharing_failure_resumes_only_a_known_task(self):
        state = {'status':'interrupted-or-failed',
            'error':"[WinError 5] Access denied: 'jobs/S04.json.partial' -> 'jobs/S04.json'"}
        self.assertTrue(worker.can_resume(state,[{'status':'in_progress','jobId':'existing'}]))
        for status in ('submitting','submission-uncertain','failed','cancelled'):
            self.assertFalse(worker.can_resume(state,[{'status':status}]))
        for message in ('HTTP 403: Access denied','[WinError 5] Access denied: input.mp4',
                        "[WinError 5] Access denied: 'jobs/S04.json'"):
            self.assertFalse(worker.can_resume({**state,'error':message},[]))

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

    def test_watchdog_does_not_finish_with_a_stale_preview(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            output = directory/'technical-preview/film-unreviewed.mp4'
            output.parent.mkdir()
            # Identity fixture only; this test never grants a media review.
            output.write_bytes(b'preview identity fixture')
            config = {'directory':str(directory),'planSha256':'plan',
                'soundtrackSha256':'audio','titlesSha256':'titles'}
            receipt = {'status':'encoded-technical-checks-passed-awaiting-semantic-review',
                'sourcePlanSha256':'plan','sourceSelectionsSha256':None,
                'soundtrackSha256':'audio','titlesSha256':'titles',
                'width':3840,'height':2160,'fps':30,'frames':6150,'seconds':205,
                'fullAudioVideoDecode':'passed','filmSha256':worker.sha(output)}
            self.assertTrue(worker.preview_complete(config,receipt))
            for key,value in (('sourcePlanSha256','other-plan'),('width',1344),
                    ('fps',24),('frames',6149),('seconds',204),
                    ('soundtrackSha256','other-audio'),('titlesSha256','other-titles'),
                    ('fullAudioVideoDecode','pending')):
                with self.subTest(key=key):
                    self.assertFalse(worker.preview_complete(config,{**receipt,key:value}))
            selections = directory/'source-selections.json'
            selections.write_text('{"version":1}',encoding='utf-8')
            self.assertFalse(worker.preview_complete(config,receipt))
            receipt['sourceSelectionsSha256'] = worker.sha(selections)
            self.assertTrue(worker.preview_complete(config,receipt))
            selections.write_text('{"version":2}',encoding='utf-8')
            self.assertFalse(worker.preview_complete(config,receipt))
            receipt['sourceSelectionsSha256'] = worker.sha(selections)
            output.write_bytes(b'changed preview')
            self.assertFalse(worker.preview_complete(config,receipt))


if __name__ == '__main__':
    unittest.main()
