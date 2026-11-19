"""Multiple prints must preserve independent motion and truthful raw provenance."""
from pathlib import Path
import sys
import unittest

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from restore_printed_regions import blend_layers, bound_mask_bottom
from restore_printed_eyes import tracked_reference_layers


class PrintedRegionsTest(unittest.TestCase):
    def test_face_mask_does_not_bleed_into_a_separate_necklace(self):
        mask = np.ones((120, 80), dtype=np.float32)
        bounded = bound_mask_bottom(mask, 90, 20)
        self.assertEqual(bounded[69, 40], 1)
        self.assertEqual(bounded[80, 40], .5)
        self.assertEqual(bounded[90, 40], 0)
        self.assertEqual(bounded[119, 40], 0)
        np.testing.assert_array_equal(mask, np.ones_like(mask))
        for bottom, feather in [(130, 20), (90, 0), (float('nan'), 10)]:
            with self.assertRaises(ValueError):
                bound_mask_bottom(mask, bottom, feather)

    def test_two_original_prints_follow_different_motion_without_changing_the_background(self):
        original = np.full((40, 80, 3), 30, dtype=np.uint8)
        mask = np.zeros((10, 10), dtype=np.float32)
        mask[2:8, 2:8] = 1
        texture = np.full((10, 10, 3), [10, 180, 220], dtype=np.float32)
        registration = np.array([[1, 0, 10], [0, 1, 10]], dtype=np.float64)
        first = tracked_reference_layers(texture, mask, registration, np.eye(3), (80, 40))
        motion = np.array([[1, 0, 40], [0, 1, 5], [0, 0, 1]], dtype=np.float64)
        second = tracked_reference_layers(texture * .5, mask, registration, motion, (80, 40))
        result = blend_layers(original, [first, second])
        np.testing.assert_array_equal(result[14, 14], [10, 180, 220])
        np.testing.assert_array_equal(result[19, 54], [5, 90, 110])
        outside = (first[1] == 0) & (second[1] == 0)
        np.testing.assert_array_equal(result[outside], original[outside])
        np.testing.assert_array_equal(original, np.full_like(original, 30))

    def test_overlapping_or_nonfinite_masks_stop_before_encoding_a_frame(self):
        image = np.zeros((4, 4, 3), dtype=np.uint8)
        texture = image.astype(np.float32)
        mask = np.ones((4, 4), dtype=np.float32)
        with self.assertRaisesRegex(ValueError, 'overlap'):
            blend_layers(image, [(texture, mask), (texture, mask)])
        mask[0, 0] = np.nan
        with self.assertRaisesRegex(ValueError, 'Finite'):
            blend_layers(image, [(texture, mask)])


if __name__ == '__main__':
    unittest.main()
