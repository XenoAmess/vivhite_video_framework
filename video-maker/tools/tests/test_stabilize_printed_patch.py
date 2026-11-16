"""A printed design must stay fixed despite changing simulated source eyes."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import cv2
import numpy as np

SPEC=importlib.util.spec_from_file_location('stabilize_printed_patch',Path(__file__).parents[1]/'stabilize_printed_patch.py')
worker=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


class PrintedSurfaceTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg is required for the encoded interval test')
    def test_unused_untrackable_tail_does_not_block_the_used_interval(self):
        rng=np.random.default_rng(29)
        first=np.full((160,220,3),70,dtype=np.uint8)
        first[48:112,78:142]=rng.integers(25,220,(64,64,3),dtype=np.uint8)
        with tempfile.TemporaryDirectory(prefix='vivhite-print-interval-') as temporary:
            source=Path(temporary)/'source.mp4'
            destination=Path(temporary)/'corrected.mp4'
            writer=cv2.VideoWriter(str(source),cv2.VideoWriter_fourcc(*'mp4v'),10,(220,160))
            self.assertTrue(writer.isOpened())
            try:
                for frame in range(10):
                    writer.write(first if frame<5 else np.zeros_like(first))
            finally:
                writer.release()
            original=worker.fingerprint(source)
            receipt=worker.stabilize(source,destination,(110,80),28,used_seconds=.5)
            self.assertEqual(worker.fingerprint(source),original)
            self.assertEqual(receipt['frames'],5)
            cap=cv2.VideoCapture(str(destination))
            try:
                decoded=0
                while cap.read()[0]:
                    decoded+=1
            finally:
                cap.release()
            self.assertEqual(decoded,5)
            saved=json.loads(destination.with_suffix('.json').read_text(encoding='utf-8'))
            self.assertEqual(saved['requestedUsedSeconds'],.5)
            self.assertEqual(saved['sourceSha256'],original)

    def test_tracking_preserves_a_print_while_the_surface_translates(self):
        rng=np.random.default_rng(23)
        first=np.full((160,220,3),70,dtype=np.uint8)
        texture=rng.integers(25,220,(64,64,3),dtype=np.uint8)
        first[48:112,78:142]=texture
        cv2.circle(first,(110,80),28,(210,190,60),2)
        cv2.circle(first,(103,80),3,(245,245,245),-1)
        cv2.circle(first,(117,80),3,(245,245,245),-1)
        tracker=worker.PrintedPatch(first,(110,80),28)
        for shift in range(1,10):
            matrix=np.float32([[1,0,shift],[0,1,0]])
            expected=cv2.warpAffine(first,matrix,(220,160))
            changed=expected.copy()
            cv2.rectangle(changed,(98+shift,75),(122+shift,85),(0,0,0),-1)
            result,metric=tracker.frame(changed)
            self.assertLess(abs(metric['center'][0]-(110+shift)),1)
            self.assertLess(float(np.mean(np.abs(result[76:84,100+shift:120+shift].astype(float)
                                                -expected[76:84,100+shift:120+shift]))),12)


if __name__=='__main__':unittest.main()
