"""Only explicitly reviewed, bound corrections may enter the technical preview.

GPL-3.0-only.
"""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).parents[1]))
from local_video_pipeline import save
from reference_finisher import sha
from render_4k_technical_preview import selected_source


class CorrectedSelectionTest(unittest.TestCase):
    def fixture(self,directory):
        original = directory/'sources/S03.mp4'
        original.parent.mkdir()
        original.write_bytes(b'unit-only original')
        corrected = directory/'corrections/S03.mp4'
        corrected.parent.mkdir()
        corrected.write_bytes(b'unit-only corrected')
        selection = {'path':'corrections/S03.mp4','sha256':sha(corrected),
            'parent':'sources/S03.mp4','parentSha256':sha(original),
            'receipt':'corrections/S03.json','inspectionReport':'corrections/inspection.json'}
        save(directory/'source-selections.json',{'sourcePlanSha256':'unit-plan','selections':{'S03':selection}})
        save(directory/'corrections/S03.json',{'sourceSha256':sha(original),'correctedSha256':sha(corrected)})
        save(directory/'corrections/inspection.json',{})
        decision = {'id':'S03','decision':'accepted','sourceSha256':sha(corrected),
            'allSourceFrameReview':True,'reviewedNativeFrames':120,
            **{key:'passed' for key in ('noHumanFaces','noAddedPeople','allCharactersFemale',
                'costumeStyle','motionAndContinuity','merchandiseBehavior','referenceAppearance')}}
        save(directory/'clip-decisions.json',{'sourcePlanSha256':'unit-plan','shots':[decision]})
        return original,corrected,decision

    def test_reviewed_correction_keeps_the_original_parent(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            original,corrected,_ = self.fixture(directory)
            actual,report = selected_source(directory,{'id':'S03','sourceSeconds':5},
                {'sourceSha256':sha(original)},'unit-plan')
            self.assertEqual(actual,corrected)
            self.assertTrue(report.is_file())
            self.assertEqual(original.read_bytes(),b'unit-only original')

    def test_rejected_or_partially_reviewed_correction_cannot_replace_the_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            original,_,decision = self.fixture(directory)
            for changes in ({'decision':'rejected'},{'reviewedNativeFrames':119},
                            {'referenceAppearance':'failed'},{'sourceSha256':'different'}):
                save(directory/'clip-decisions.json',{'sourcePlanSha256':'unit-plan','shots':[{**decision,**changes}]})
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    selected_source(directory,{'id':'S03','sourceSeconds':5},{'sourceSha256':sha(original)},'unit-plan')

    def test_changed_parent_corrected_file_or_plan_blocks_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            original,corrected,_ = self.fixture(directory)
            job = {'sourceSha256':sha(original)}
            with self.assertRaises(ValueError):
                selected_source(directory,{'id':'S03','sourceSeconds':5},job,'other-plan')
            corrected.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                selected_source(directory,{'id':'S03','sourceSeconds':5},job,'unit-plan')
            corrected.write_bytes(b'unit-only corrected')
            original.write_bytes(b'changed parent')
            with self.assertRaises(ValueError):
                selected_source(directory,{'id':'S03','sourceSeconds':5},job,'unit-plan')


if __name__ == '__main__':
    unittest.main()
