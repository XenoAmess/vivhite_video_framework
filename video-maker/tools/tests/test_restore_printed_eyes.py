"""Validate artwork registration and mask scope, never semantic acceptance."""
from pathlib import Path
import sys
import unittest

import cv2
import numpy as np

sys.path.insert(0,str(Path(__file__).parents[1]))
import restore_printed_eyes as worker


class PrintedEyeRestorationTest(unittest.TestCase):
    def test_registration_matches_both_landmarks_without_mirroring(self):
        before = np.float32([[455,545],[705,520]])
        after = np.float32([[2427,1174],[2515,1158]])
        matrix = worker.eye_registration(before,after)
        np.testing.assert_allclose(cv2.transform(before[None],matrix)[0],after,atol=.001)
        self.assertGreater(np.linalg.det(matrix[:,:2]),0)
        with self.assertRaises(ValueError):
            worker.eye_registration([1,1,1,1],[1,1,2,2])

    def test_mask_does_not_replace_the_whole_head_or_transparent_areas(self):
        reference = np.full((900,1100,4),255,dtype=np.uint8)
        reference[:100,:,3] = 0
        texture,mask,_ = worker.projected_eyes(reference,[455,545,705,520],
            [2427,1174,2515,1158],(3840,2160),[.9,.87,.76])
        self.assertEqual(mask[1000,2460],0)
        self.assertEqual(mask[1300,2460],0)
        self.assertGreater(mask[1174,2427],.95)
        self.assertGreater(mask[1158,2515],.95)
        self.assertTrue(np.all(texture[1174,2427] < 255))
        with self.assertRaises(ValueError):
            worker.projected_eyes(reference[:,:,:3],[455,545,705,520],
                [2427,1174,2515,1158],(3840,2160),[1,1,1])


if __name__ == '__main__':
    unittest.main()
