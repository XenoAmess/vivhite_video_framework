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

    def test_smaller_reference_masks_stay_near_the_eyes(self):
        reference = np.full((256,256,4),255,dtype=np.uint8)
        eyes = [80,120,170,120]
        _,small,_ = worker.projected_eyes(reference,eyes,eyes,(256,256),[1,1,1],.36)
        _,original,_ = worker.projected_eyes(reference,eyes,eyes,(256,256),[1,1,1])
        self.assertGreater(small[120,80],.95)
        self.assertLess(small[70,80],.001)
        self.assertGreater(original[70,80],.1)
        for scale in (0,float('nan'),float('inf'),5):
            with self.subTest(scale=scale),self.assertRaises(ValueError):
                worker.projected_eyes(reference,eyes,eyes,(256,256),[1,1,1],scale)

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

    def test_current_frame_projection_preserves_a_patch_entering_from_the_bottom(self):
        reference = np.full((256,256,4),255,dtype=np.uint8)
        reference[:,:,:3] = np.indices((256,256))[0][:,:,None]
        eyes,target,size = [80,100,170,100],[80,150,170,150],(256,160)
        texture,mask = worker.reference_eye_layers(reference,eyes,[1,1,1],.55)
        first_texture,first_mask,registration = worker.projected_eyes(reference,eyes,target,size,[1,1,1],.55)
        motion = np.array([[1,0,0],[0,1,-60],[0,0,1]],dtype=np.float64)
        current_texture,current_mask = worker.tracked_reference_layers(texture,mask,registration,motion,size)
        clipped_mask = cv2.warpPerspective(first_mask,motion,size)
        self.assertEqual(clipped_mask[130,80],0)
        self.assertGreater(current_mask[130,80],.65)
        np.testing.assert_array_equal(current_texture[130,80],reference[140,80,:3])
        actual = worker.tracked_reference_layers(texture,mask,registration,np.eye(3),size)
        np.testing.assert_allclose(actual[0],first_texture)
        np.testing.assert_allclose(actual[1],first_mask)

    def test_current_frame_projection_keeps_original_reference_transparency(self):
        reference = np.full((256,256,4),255,dtype=np.uint8)
        reference[135:145,75:86,3] = 0
        texture,mask = worker.reference_eye_layers(reference,[80,100,170,100],[1,1,1],.55)
        registration = worker.eye_registration([80,100,170,100],[80,150,170,150])
        motion = np.array([[1,0,0],[0,1,-60],[0,0,1]],dtype=np.float64)
        _,current_mask = worker.tracked_reference_layers(texture,mask,registration,motion,(256,160))
        self.assertEqual(current_mask[130,80],0)
        with self.assertRaises(ValueError):
            worker.tracked_reference_layers(texture,mask,registration,np.full((3,3),np.nan),(256,160))


if __name__ == '__main__':
    unittest.main()
