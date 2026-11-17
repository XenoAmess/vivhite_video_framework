"""Real media tests for resolution claims and stale picture cache rejection."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).parents[1]))
import local_video_finisher as finisher
import reference_finisher as worker
from inspect_local_video_film import validate_timing


class LocalFinisherTest(unittest.TestCase):
    def test_only_declared_ten_second_s20_is_allowed_by_final_inspection(self):
        valid = {'fps':30,'shotDurationExceptions':{'S20':10},'shots':[{'id':'S20','seconds':10}]}
        validate_timing(valid)
        for altered in ({'fps':30,'shots':[{'id':'S20','seconds':10}]},
                        {'fps':30,'shotDurationExceptions':{'S21':10},'shots':[{'id':'S21','seconds':10}]},
                        {'fps':30,'shotDurationExceptions':{'S20':10},'shots':[{'id':'S20','seconds':9}]}):
            with self.subTest(plan=altered), self.assertRaisesRegex(ValueError,'exception'):
                validate_timing(altered)

    def test_ten_second_source_remains_300_frames_and_retains_its_exception(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'sources').mkdir()
            worker.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=s=1344x768:r=24:d=10',
                        '-frames:v','240','-c:v','libx264','-preset','ultrafast',str(root/'sources/S20.mp4')])
            plan = {'schemaVersion':'vivhite-local-two-stage-video-1','stage':'draft','model':'fasth3-omni-bf16',
                'width':1344,'height':768,'sourceSize':'1344x768','fps':30,'sourceFps':24,'maxShotSeconds':5,
                'shotDurationExceptions':{'S20':10},'totalFrames':300,'titleOverlays':[],'closingCredit':'',
                **{key:True for key in ('noSpeech','noHumanFaces','noAddedPeople','allCharactersFemale')},
                'shots':[{'id':'S20','seconds':10,'sourceSeconds':10,'startFrame':0,'prompt':'Unit fixture.'}]}
            worker.write_json(root/'plan.json',plan)
            (root/'clip-decisions.json').write_text('{}')
            (root/'soundtrack.wav').write_bytes(b'unit fixture audio, not a semantic approval')
            with patch.object(worker,'verify_clip_decisions'):
                final = finisher.prepare(root/'plan.json',root,root/'final.json')
            validate_timing(final)
            self.assertEqual(final['shotDurationExceptions'],{'S20':10})
            probe = json.loads(worker.run(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',
                                           str(root/'picture-assembly.mp4')]))
            self.assertEqual(int(probe['streams'][0]['nb_read_frames']),300)
            self.assertEqual(float(probe['streams'][0]['duration']),10)

    def test_final_inspection_accepts_both_real_long_shots_but_not_undeclared_closing(self):
        plan = {'fps':30,'shotDurationExceptions':{'S20':10,'S48':10},
                'shots':[{'id':'S20','seconds':10},{'id':'S48','seconds':10}]}
        validate_timing(plan)
        with self.assertRaisesRegex(ValueError,'exception'):
            validate_timing({**plan,'shotDurationExceptions':{'S20':10}})
        with self.assertRaisesRegex(ValueError,'exception'):
            validate_timing({**plan,'shots':[{'id':'S20','seconds':10}]})

    def test_native_size_assembly_preserves_old_result_when_a_source_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'sources').mkdir()
            source = root/'sources/S20A.mp4'
            def video(color):
                worker.run(['ffmpeg','-v','error','-y','-f','lavfi','-i',f'color=c={color}:s=1344x768:r=24',
                            '-frames:v','120','-c:v','libx264','-preset','ultrafast',str(source)])
            video('blue')
            plan = {'schemaVersion':'vivhite-local-two-stage-video-1','stage':'draft','model':'fasth3-omni-bf16',
                'width':1344,'height':768,'sourceSize':'1344x768','fps':30,'sourceFps':24,'maxShotSeconds':5,
                'totalFrames':60,'titleOverlays':[],'closingCredit':'',
                **{k:True for k in ('noSpeech','noHumanFaces','noAddedPeople','allCharactersFemale')},
                'shots':[{'id':'S20A','seconds':2,'sourceSeconds':5,'startFrame':0,'prompt':'Quiet lake.'}]}
            plan_file = root/'plan.json'
            worker.write_json(plan_file,plan)
            # Fixtures explicitly bypass semantic decisions; this test does not
            # record an approval or invoke the formal finishing gate.
            (root/'clip-decisions.json').write_text('{}',encoding='utf-8')
            (root/'soundtrack.wav').write_bytes(b'unit fixture, not an audited audio file')
            (root/'source-imports.json').write_text('{"scope":"unit fixture provenance"}',encoding='utf-8')
            with patch.object(worker,'verify_clip_decisions'):
                result = finisher.prepare(plan_file,root,root/'final.json')
                self.assertEqual((result['width'],result['height']),(1344,768))
                self.assertIn('source-imports.json',{item['path'] for item in result['files']})
                probe = json.loads(worker.run(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',
                                               str(root/'picture-assembly.mp4')]))
                self.assertEqual(int(probe['streams'][0]['nb_read_frames']),60)
                old_picture = worker.sha(root/'picture-assembly.mp4')
                video('green')
                with self.assertRaisesRegex(ValueError,'Changed source'):
                    finisher.prepare(plan_file,root,root/'replacement.json')
                self.assertEqual(worker.sha(root/'picture-assembly.mp4'),old_picture)
                bad = copy.deepcopy(plan)
                bad.update(stage='refine',model='open-h3-2k',width=2560,height=1440,sourceSize='2560x1440')
                worker.write_json(root/'2k-plan.json',bad)
                with self.assertRaisesRegex(ValueError,'native resolution'):
                    finisher.prepare(root/'2k-plan.json',root,root/'false-2k.json')


if __name__ == '__main__':
    unittest.main()
