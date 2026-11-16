"""Actual retiming and replacement binding checks for reviewed source corrections."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).parents[1]))
from local_video_pipeline import save
from reference_finisher import sha
from record_local_clip_review import record
from retime_local_clip import retime


class LocalClipCorrectionTest(unittest.TestCase):
    def test_real_slow_motion_has_exact_length_and_preserves_original_and_prior_candidate(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source,destination = directory/'original.mp4',directory/'slow.mp4'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=s=96x64:r=24:d=2',
                            '-c:v','libx264','-pix_fmt','yuv420p',str(source)],check=True)
            original_hash = sha(source)
            receipt = retime(source,destination,3,'Slow the actual moving test fixture.')
            self.assertEqual(receipt['nativeSize'],[96,64])
            self.assertEqual(receipt['durationSeconds'],5)
            self.assertEqual(receipt['semanticReview'],'pending')
            self.assertEqual(sha(source),original_hash)
            result_hash = sha(destination)
            with self.assertRaisesRegex(ValueError,'Preserve this output'):
                retime(source,destination,4,'A separate timing requires a separate path.')
            self.assertEqual(sha(destination),result_hash)

    def test_correction_review_binds_selected_bytes_and_changed_parent_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            original,corrected = directory/'original.mp4',directory/'corrected.mp4'
            original.write_bytes(b'original fixture')
            corrected.write_bytes(b'corrected fixture')
            save(directory/'plan.json',{'shots':[{'id':'S48','seconds':5}]})
            save(directory/'correction.json',{'scope':'fixture'})
            save(directory/'inspection.json',{'identity':{'sourceSha256':sha(corrected),'usedSeconds':5},
                'usedFramesAnalysed':120,'allUsedFrameEvidence':[],'faceEvidence':None})
            save(directory/'source-selections.json',{'selections':{'S48':{'path':'corrected.mp4',
                'sha256':sha(corrected),'parent':'original.mp4','parentSha256':sha(original),
                'receipt':'correction.json','inspectionReport':'inspection.json'}}})
            record(directory/'plan.json',directory,'S48','All fixture frames explicitly reviewed.',True,True)
            decision = json.loads((directory/'clip-decisions.json').read_text())['shots'][0]
            self.assertEqual(decision['sourceSha256'],sha(corrected))
            original.write_bytes(b'changed fixture parent')
            with self.assertRaisesRegex(ValueError,'parent changed'):
                record(directory/'plan.json',directory,'S48','Cannot reuse changed evidence.',True,True)

    def test_long_source_needs_all_frames_and_explicit_artwork_comparison(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory/'sources').mkdir()
            source = directory/'sources/S20.mp4'
            source.write_bytes(b'ten second fixture')
            plan = directory/'plan.json'
            save(plan,{'referenceAppearanceRequired':True,'shots':[{'id':'S20','seconds':10,'sourceSeconds':10}]})
            report = {'identity':{'sourceSha256':sha(source),'usedSeconds':10},
                      'usedFramesAnalysed':120,'allUsedFrameEvidence':[],'faceEvidence':None}
            save(directory/'clip-inspection/S20.json',report)
            with self.assertRaisesRegex(ValueError,'original artwork'):
                record(plan,directory,'S20','Explicit fixture review.',True,True)
            with self.assertRaisesRegex(ValueError,'complete actual source'):
                record(plan,directory,'S20','Explicit fixture review.',True,True,reference_fidelity_reviewed=True)
            report['usedFramesAnalysed'] = 240
            save(directory/'clip-inspection/S20.json',report)
            record(plan,directory,'S20','All fixture frames and reference explicitly compared.',True,True,
                   reference_fidelity_reviewed=True)
            row = json.loads((directory/'clip-decisions.json').read_text())['shots'][0]
            self.assertEqual(row['reviewedNativeFrames'],240)
            self.assertEqual(row['referenceAppearance'],'passed')


if __name__ == '__main__':
    unittest.main()
