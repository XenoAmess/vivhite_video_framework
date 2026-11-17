"""Verify native UHD preparation preserves complete reviewed source intervals.

Semantic gates are explicit unit stubs, never real production approvals.
GPL-3.0-only.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import prepare_local_refinement as worker


@unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg required for complete source fixtures')
class NativeFourKPreparationTest(unittest.TestCase):
    def exercise(self, reviewed_frames):
        with tempfile.TemporaryDirectory(prefix='vivhite-uhd-input-') as temporary:
            root = Path(temporary)
            draft, refined = root / 'draft', root / '4k'
            (draft / 'sources').mkdir(parents=True)
            source = draft / 'sources/S48.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                            'color=blue:s=1344x768:r=24', '-frames:v', '360',
                            '-c:v', 'libx264', '-preset', 'ultrafast', str(source)], check=True)
            digest = worker.sha(source)
            # This fake delivery only exercises preparation bookkeeping. The
            # formal gate is stubbed below; nothing is submitted or approved.
            (draft / 'film.mp4').write_bytes(b'unit fixture, not a delivered film')
            for name in ('soundtrack.wav', 'soundtrack-receipt.json'):
                (draft / name).write_bytes(b'unit audio fixture')
            (draft/'titles.ass').write_text('unit titles',encoding='utf-8')
            (root/'review.json').write_text('{}',encoding='utf-8')
            plan = {'schemaVersion':'vivhite-local-two-stage-video-1', 'stage':'draft',
                    'model':'fasth3-omni-bf16', 'width':1344, 'height':768,
                    'sourceSize':'1344x768', 'sourceFps':24, 'fps':30, 'maxShotSeconds':5,
                    'totalFrames':420, 'shotDurationExceptions':{'S48':14},
                    **{key:True for key in ('noSpeech','noHumanFaces','noAddedPeople','allCharactersFemale')},
                    'refinement':{'size':'2560x1440','status':'historical-stopped'},
                    'shots':[{'id':'S48','seconds':14,'sourceSeconds':15,'startFrame':0,
                              'prompt':'Quiet coast.','generationAction':'Slow wings.',
                              'mode':'I','references':['unit-scene.png']}]}
            def save(path, value):
                path.write_text(json.dumps(value), encoding='utf-8')
            plan_file, final_file, delivery_file = (root / name for name in
                                                   ('draft-plan.json','assembly.json','delivery.json'))
            save(plan_file, plan)
            save(final_file, {'shots':[{'id':'S48','sourceFile':'sources/S48.mp4'}],
                              'files':[{'path':'sources/S48.mp4','sha256':digest}]})
            save(draft / 'clip-decisions.json', {'shots':[{'id':'S48',
                 'allSourceFrameReview':True,'reviewedNativeFrames':reviewed_frames}]})
            save(delivery_file, {'schemaVersion':'vivhite-delivery-plan-1',
                 'film':{'sha256':worker.sha(draft / 'film.mp4'),'frames':420},
                 'machineDecodedFinalFrames':420,'finalAssemblyPlan':final_file.name,
                 'finalReview':'review.json','finalReviewSha256':worker.sha(root/'review.json'),
                 'finalAssemblyPlanSha256':worker.sha(final_file)})
            real_run = worker.run
            def unit_run(command, **kwargs):
                if len(command)>1 and str(command[1]).endswith('character_review.py'):
                    self.assertEqual(command.count('--asset'),5)
                    self.assertIn(str(draft/'titles.ass'),command)
                    self.assertIn(str(root/'review.json'),command)
                    return 'Unit-only semantic gate stub; no production approval'
                return real_run(command, **kwargs)
            with patch.object(worker,'run',side_effect=unit_run), patch.object(worker,'verify_clip_decisions'):
                if reviewed_frames < 360:
                    with self.assertRaisesRegex(ValueError,'complete 4K input'):
                        worker.prepare(root/'episode.json',plan_file,draft,delivery_file,refined,
                                       root/'refined-plan.json',root)
                    self.assertFalse((root/'refined-plan.json').exists())
                    return
                worker.prepare(root/'episode.json',plan_file,draft,delivery_file,refined,
                               root/'refined-plan.json',root)
            result = json.loads((root/'refined-plan.json').read_text())
            self.assertEqual((result['width'], result['height'], result['sourceSize']),
                             (3840,2160,'3840x2160'))
            self.assertEqual(result['model'],'open-h3-2k')
            self.assertEqual(result['refinement']['submissionWindow'],1)
            self.assertEqual(result['refinement']['size'],'3840x2160')
            self.assertNotIn('historical-stopped', json.dumps(result['refinement']))
            self.assertEqual((result['shots'][0]['seconds'], result['shots'][0]['sourceSeconds']), (14,15))
            self.assertIn('3840x2160',result['shots'][0]['prompt'])
            self.assertIn('EXACT ORIGINAL SPEED',result['shots'][0]['prompt'])
            self.assertNotIn('Slow wings.',result['shots'][0]['prompt'])
            self.assertNotIn('very slow',result['shots'][0]['prompt'])
            self.assertNotIn('four seconds',result['shots'][0]['prompt'])
            self.assertNotIn('references',result['shots'][0])
            self.assertEqual(worker.sha(refined/'input-sources/S48.mp4'),digest)
            self.assertEqual(worker.sha(source),digest)

    def test_native_4k_plan_preserves_all_fifteen_source_seconds_and_fourteen_final_seconds(self):
        self.exercise(360)

    def test_unreviewed_last_source_second_blocks_4k_preparation(self):
        self.exercise(336)


class SelectedVideoPromptTest(unittest.TestCase):
    def test_refinement_does_not_reenact_historical_image_prompt(self):
        for identity in ('S01','S05','S07','S15','S20','S28','S44','S47','S48'):
            with self.subTest(identity=identity):
                prompt = worker.refinement_prompt({'id':identity,'mode':'H',
                    'generationAction':'REJECTED historical action <Picture 1> <Video 1>'})
                self.assertIn('INPUT VIDEO',prompt)
                self.assertNotIn('REJECTED',prompt)
                self.assertNotIn('<Picture',prompt)
                self.assertNotIn('<Video',prompt)
                self.assertIn('No real human face',prompt)
        self.assertIn('LEFT backhand',worker.refinement_prompt({'id':'S01','mode':'H'}))
        self.assertIn('CLOSED',worker.refinement_prompt({'id':'S44','mode':'H'}))
        self.assertIn('two uncrossed attached arms',worker.refinement_prompt({'id':'S47','mode':'H'}))


if __name__ == '__main__':
    unittest.main()
