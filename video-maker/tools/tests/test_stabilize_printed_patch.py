"""A printed design must stay fixed despite changing simulated source eyes."""
import importlib.util
from pathlib import Path
import unittest
import cv2
import numpy as np

SPEC=importlib.util.spec_from_file_location('stabilize_printed_patch',Path(__file__).parents[1]/'stabilize_printed_patch.py')
worker=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


class PrintedSurfaceTest(unittest.TestCase):
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
