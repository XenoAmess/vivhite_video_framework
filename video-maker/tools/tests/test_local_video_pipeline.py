"""Transport, recovery and actual frame-boundary tests for the local two-stage worker."""
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).parents[1]))
import local_video_pipeline as worker


class LocalPipelineTest(unittest.TestCase):
    def test_reused_source_is_bound_and_a_changed_copy_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory/'accepted.mp4'
            source.write_bytes(b'previously reviewed source bytes')
            plan = {'stage':'refine','shots':[],
                    'reusedSources':[{'path':'accepted.mp4','sha256':worker.sha(source)}]}
            self.assertEqual(worker.input_assets(plan,directory/'episode.json',directory),[source])
            source.write_bytes(b'different unreviewed source')
            with self.assertRaisesRegex(ValueError,'reused reviewed source changed'):
                worker.input_assets(plan,directory/'episode.json',directory)

    def plan(self):
        return {'schemaVersion':'vivhite-local-two-stage-video-1','stage':'draft',
                'model':'fasth3-omni-bf16','width':1344,'height':768,'fps':30,'sourceFps':24,
                'maxShotSeconds':5,'totalFrames':300,
                **{key:True for key in ('noSpeech','noHumanFaces','noAddedPeople','allCharactersFemale')},
                'shots':[{'id':identity,'seconds':5,'sourceSeconds':5,'startFrame':index*150,'prompt':'Quiet lake.'}
                         for index,identity in enumerate(('S20A','S20B'))]}

    def test_split_shot_ids_and_five_second_limit_are_enforced(self):
        plan = self.plan()
        worker.validate(plan)
        for field,value in (('seconds',6),('startFrame',149),('id','S20A')):
            bad = copy.deepcopy(plan)
            bad['shots'][1][field] = value
            with self.assertRaises(ValueError):
                worker.validate(bad)

    def test_reference_fields_match_both_documented_endpoints(self):
        upload = lambda path:{'file_id':'file_'+path}
        draft = worker.payload_for({'stage':'draft'},
            {'seed':7,'prompt':'Keep quiet.','references':['image'],'motionReference':'motion'},upload)
        self.assertEqual(draft['model'],'fasth3-omni-bf16')
        self.assertEqual(draft['video_reference'],[{'file_id':'file_motion'}])
        self.assertIsInstance(draft['seconds'],int)
        refined = worker.payload_for({'stage':'refine'}, {'prompt':'Preserve.','inputSource':'draft'},upload)
        self.assertEqual(refined['input_video'],{'file_id':'file_draft'})
        self.assertEqual(refined['size'],'2560x1440')
        self.assertNotIn('image_reference',refined)

    def test_ten_second_lake_requires_its_specific_declared_exception(self):
        plan = self.plan()
        plan['shots'][0].update(id='S20',seconds=10,sourceSeconds=10,seed=20,references=['lake.png'])
        plan['shots'][1].update(id='S21',startFrame=300)
        plan['totalFrames'] = 450
        with self.assertRaises(ValueError):
            worker.validate(plan)
        plan['shotDurationExceptions'] = {'S20':10}
        worker.validate(plan)
        self.assertEqual(worker.source_frame_count(plan['shots'][0]),240)
        request = worker.payload_for(plan,plan['shots'][0],lambda path:{'file_id':'file_lake'})
        self.assertEqual(request['seconds'],10)
        for exceptions in ({'S21':10},{'S20':15},{'S20':10,'S21':10}):
            with self.subTest(exceptions=exceptions), self.assertRaises(ValueError):
                worker.validate({**plan,'shotDurationExceptions':exceptions})

    def test_image_only_generation_never_uploads_an_old_motion_reference(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for name in ('scene.png','master.png'):
                (directory/name).write_bytes(name.encode('ascii'))
            shot = {'seed':17,'prompt':'Keep the original print.','references':['scene.png','master.png']}
            assets = worker.input_assets({'stage':'draft','shots':[shot]},directory/'episode.json',directory)
            self.assertEqual(assets,[directory/'scene.png',directory/'master.png'])
            uploaded = []
            def upload(path):
                uploaded.append(path)
                return {'file_id':'file_'+path}
            request = worker.payload_for({'stage':'draft'},shot,upload)
            self.assertEqual(uploaded,['scene.png','master.png'])
            self.assertNotIn('video_reference',request)
            self.assertEqual(request['task'],'ref2va')

    def test_disconnect_after_post_is_retained_and_cannot_duplicate_submission(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'job.json'
            receipt = {'status':'prepared'}
            class Disconnected:
                calls = 0
                def json(self,*args):
                    self.calls += 1
                    raise TimeoutError('Reply lost after possible acceptance')
            api = Disconnected()
            with self.assertRaises(TimeoutError):
                worker.submit(api,'/videos',{'prompt':'Quiet'},path,receipt)
            self.assertEqual(worker.read(path)['status'],'submission-uncertain')
            with self.assertRaisesRegex(RuntimeError,'Ambiguous'):
                worker.submit(api,'/videos',{'prompt':'Quiet'},path,receipt)
            self.assertEqual(api.calls,1)

    def test_queue_full_is_a_known_rejection_that_can_be_retried(self):
        with tempfile.TemporaryDirectory() as temporary:
            class Full:
                def json(self,*args):
                    raise worker.ApiError(429,'full')
            receipt = {'status':'prepared'}
            self.assertFalse(worker.submit(Full(),'/videos',{},Path(temporary)/'job.json',receipt))
            self.assertEqual(receipt['status'],'prepared')

    def test_upload_and_health_use_real_http_and_correct_roots(self):
        seen = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):
                pass
            def do_GET(self):
                seen.append(self.path)
                data = b'{"status":"ok"}'
                self.send_response(200); self.end_headers(); self.wfile.write(data)
            def do_POST(self):
                seen.append((self.path,self.headers['Content-Type'],self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(200); self.end_headers(); self.wfile.write(b'{"id":"file_real"}')
        server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread = threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            api = worker.Api(f'http://127.0.0.1:{server.server_port}/v1')
            self.assertEqual(api.json('GET','/../health')['status'],'ok')
            with tempfile.TemporaryDirectory() as temporary:
                source = Path(temporary)/'reference.dat'
                source.write_bytes(b'actual reference contents')
                self.assertEqual(api.upload(source)['id'],'file_real')
            self.assertEqual(seen[0],'/health')
            self.assertEqual(seen[1][0],'/v1/files')
            self.assertIn(b'actual reference contents',seen[1][2])
            self.assertIn('multipart/form-data',seen[1][1])
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_raw_alignment_frames_are_preserved_while_input_is_exactly_five_seconds(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root/'original.mp4'
            worker.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=blue:s=64x32:r=24',
                        '-frames:v','124','-c:v','libx264',str(original)])
            contents = original.read_bytes()
            digest = worker.sha(original)
            class Download:
                def request(self,*args,**kwargs):
                    return original.open('rb')
            raw,source,probe = worker.publish_result(Download(),{'id':'video_test','result':{'sha256':digest}},
                                                     {'id':'S20A'},root,'64x32')
            self.assertEqual(raw.read_bytes(),contents)
            self.assertEqual(int(probe['streams'][0]['nb_read_frames']),124)
            actual = json.loads(worker.run(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(source)]))
            self.assertEqual(int(actual['streams'][0]['nb_read_frames']),120)
            self.assertEqual(float(actual['streams'][0]['duration']),5)

    def test_ten_second_result_preserves_raw_and_keeps_all_240_review_frames(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root/'original.mp4'
            worker.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=64x32:r=24',
                        '-frames:v','244','-c:v','libx264',str(original)])
            contents = original.read_bytes()
            class Download:
                def request(self,*args,**kwargs):
                    return original.open('rb')
            raw,source,probe = worker.publish_result(Download(),{'id':'video_long','result':{'sha256':worker.sha(original)}},
                                                     {'id':'S20','sourceSeconds':10},root,'64x32')
            self.assertEqual(raw.read_bytes(),contents)
            self.assertEqual(int(probe['streams'][0]['nb_read_frames']),244)
            actual = json.loads(worker.run(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(source)]))
            self.assertEqual(int(actual['streams'][0]['nb_read_frames']),240)
            self.assertEqual(float(actual['streams'][0]['duration']),10)


if __name__ == '__main__':
    unittest.main()
