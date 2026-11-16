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


class LocalFinisherTest(unittest.TestCase):
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
            with patch.object(worker,'verify_clip_decisions'):
                result = finisher.prepare(plan_file,root,root/'final.json')
                self.assertEqual((result['width'],result['height']),(1344,768))
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
