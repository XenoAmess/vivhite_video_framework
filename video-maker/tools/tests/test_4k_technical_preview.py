"""Real native-UHD fixture encode, with an explicit unit-only semantic gate stub.

No production review is generated or approved. GPL-3.0-only.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

sys.path.insert(0,str(Path(__file__).parents[1]))
import render_4k_technical_preview as worker


@unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg required for native-UHD fixture')
class NativeTechnicalPreviewTest(unittest.TestCase):
    def test_playable_native_preview_never_issues_formal_or_semantic_approval(self):
        with tempfile.TemporaryDirectory(prefix='vivhite-native-preview-test-') as temporary:
            root = Path(temporary)
            directory = root/'run'
            (directory/'sources').mkdir(parents=True)
            (directory/'input-sources').mkdir()
            for folder in ('jobs','clip-inspection'):
                (directory/folder).mkdir()
            source = directory/'sources/S01.mp4'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=blue:s=3840x2160:r=24',
                '-frames:v','120','-c:v','libx264','-preset','ultrafast','-crf','35','-pix_fmt','yuv420p',str(source)],check=True)
            input_source = directory/'input-sources/S01.mp4'
            shutil.copyfile(source,input_source)
            digest = worker.sha(source)
            plan = {'schemaVersion':'vivhite-local-two-stage-video-1','stage':'refine','model':'open-h3-2k',
                'width':3840,'height':2160,'sourceSize':'3840x2160','sourceFps':24,'fps':30,
                'maxShotSeconds':5,'totalFrames':60,'titleOverlays':[],'closingCredit':'',
                **{k:True for k in ('noSpeech','noHumanFaces','noAddedPeople','allCharactersFemale')},
                'shots':[{'id':'S01','seconds':2,'sourceSeconds':5,'startFrame':0,'mode':'W',
                    'prompt':'Unit blue native-UHD fixture, no production scene.',
                    'inputSource':'input-sources/S01.mp4','inputSourceSha256':digest}]}
            def save(path,data):
                path.write_text(json.dumps(data),encoding='utf-8')
            plan_file = root/'plan.json'
            save(plan_file,plan)
            save(directory/'jobs/S01.json',{'status':'completed','sourceSha256':digest,'planSha256':worker.sha(plan_file)})
            save(directory/'clip-inspection/S01.json',{'status':'decoded',
                'identity':{'sourceSha256':digest},'decodedFrames':120})
            with wave.open(str(directory/'soundtrack.wav'),'wb') as audio:
                audio.setparams((2,2,48000,0,'NONE','not compressed'))
                audio.writeframes(b'\0'*(2*48000*2*2))
            titles = root/'expected.ass'
            titles.write_text(worker.titles(plan),encoding='utf-8-sig',newline='\n')
            config_file = root/'config.json'
            save(config_file,{'root':str(root),'directory':str(directory),'episode':str(root/'episode.json'),
                'plan':str(plan_file),'planSha256':worker.sha(plan_file),
                'soundtrackSha256':worker.sha(directory/'soundtrack.wav'),'titlesSha256':worker.sha(titles)})
            real_run = worker.run
            def unit_run(command,**kwargs):
                if len(command)>1 and str(command[1]).endswith('character_review.py'):
                    return 'Unit-only gate stub, no production approval'
                return real_run(command,**kwargs)
            with patch.object(worker,'run',side_effect=unit_run):
                worker.build(config_file)
            preview = directory/'technical-preview'
            receipt = json.loads((preview/'receipt.json').read_text(encoding='utf-8'))
            self.assertEqual((receipt['width'],receipt['height'],receipt['frames'],receipt['seconds']),
                             (3840,2160,60,2))
            self.assertEqual(receipt['fullAudioVideoDecode'],'passed')
            self.assertEqual(receipt['semanticReview'],'pending')
            self.assertFalse(receipt['formalDelivery'])
            self.assertFalse(receipt['releasePublished'])
            self.assertFalse((directory/'film.mp4').exists())
            self.assertFalse((directory/'clip-decisions.json').exists())
            self.assertEqual(worker.sha(source),digest)
            before = worker.sha(preview/'film-unreviewed.mp4')
            worker.build(config_file)
            self.assertEqual(worker.sha(preview/'film-unreviewed.mp4'),before)


if __name__ == '__main__':
    unittest.main()
