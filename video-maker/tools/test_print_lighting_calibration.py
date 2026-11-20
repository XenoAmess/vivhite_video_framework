"""Check light measurement without equating an image metric with approval."""
import unittest
import numpy as np
from print_lighting_calibration import estimate_skin_gain


class PrintLightingCalibrationTest(unittest.TestCase):
    def test_recovers_dark_warm_illumination_and_ignores_eye_damage(self):
        reference = np.full((240, 240, 4), [190, 225, 250, 255], np.uint8)
        source = reference[:, :, :3].astype(np.float32) * [.48, .60, .72]
        source[85:116, 65:96] = [240, 30, 30]
        source[85:116, 145:176] = [10, 250, 10]
        result = estimate_skin_gain(reference, source.astype(np.uint8),
            np.eye(3)[:2], [80, 100, 160, 100], np.ones((240, 240)))
        np.testing.assert_allclose(result['proposedGainRgb'], [.72, .60, .48], atol=.006)

    def test_refuses_unavailable_skin_instead_of_inventing_a_gain(self):
        reference = np.full((240, 240, 4), 255, np.uint8)
        with self.assertRaisesRegex(ValueError, 'Insufficient visible'):
            estimate_skin_gain(reference, reference[:, :, :3], np.eye(3)[:2],
                [80, 100, 160, 100], np.ones((240, 240)))

    def test_large_original_master_does_not_exceed_remap_dimension_limit(self):
        reference = np.full((1000, 1000, 4), [190, 225, 250, 255], np.uint8)
        source = reference[:, :, :3].astype(np.float32) * [.48, .60, .72]
        result = estimate_skin_gain(reference, source.astype(np.uint8), np.eye(3)[:2],
            [250, 400, 750, 400], np.ones((1000, 1000)))
        self.assertGreater(result['samplePixels'], 32767)
        np.testing.assert_allclose(result['proposedGainRgb'], [.72, .60, .48], atol=.006)


if __name__ == '__main__':
    unittest.main()
