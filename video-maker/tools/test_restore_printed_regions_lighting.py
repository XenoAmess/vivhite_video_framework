"""Validate local gain, registration and bounded softness independently of video."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

import restore_printed_regions_lighting as worker


class PrintLightingRestorationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.reference = Path(self.temp.name) / 'original.png'
        cv2.imwrite(str(self.reference), np.full((240, 240, 4), [190, 225, 250, 255], np.uint8))
        self.definition = {'id': 'test-print', 'reference': str(self.reference),
            'referenceSha256': worker.fingerprint(self.reference), 'referenceEyes': [80, 100, 160, 100],
            'targetEyes': [110, 150, 190, 150], 'gainRgb': [.6, .5, .4], 'maskScale': .5,
            'referenceSofteningSigma': .5, 'trackingCenter': [700, 400], 'trackingRadius': 50}
        self.first = np.full((240, 400, 3), 100, np.uint8)

    def test_applies_local_rgb_gain_and_keeps_original_input_untouched(self):
        before = self.first.copy()
        with patch.object(worker, 'PrintedPatch'):
            region = worker.prepare_regions(self.first, [self.definition])[0]
        np.testing.assert_allclose(region['texture'][120, 120], [76, 112.5, 150], atol=.001)
        np.testing.assert_array_equal(self.first, before)

    def test_preserves_bound_three_point_geometry(self):
        definition = dict(self.definition, registrationMode='three-point-affine-face',
            referenceLandmarks=[[80, 100], [160, 100], [120, 160]],
            targetLandmarks=[[110, 150], [190, 150], [150, 216]])
        with patch.object(worker, 'PrintedPatch'):
            region = worker.prepare_regions(self.first, [definition])[0]
        original = np.column_stack((definition['referenceLandmarks'], np.ones(3)))
        np.testing.assert_allclose(original @ region['registration'].T, definition['targetLandmarks'], atol=.001)

    def test_refuses_overblur_and_changed_artwork(self):
        with self.assertRaisesRegex(ValueError, 'softening'):
            worker.prepare_regions(self.first, [dict(self.definition, referenceSofteningSigma=20)])
        with self.assertRaisesRegex(ValueError, 'Original artwork changed'):
            worker.prepare_regions(self.first, [dict(self.definition, referenceSha256='wrong')])

    def test_smooth_curve_preserves_endpoints_and_warm_light_change(self):
        definition = dict(self.definition, gainRgbKeyframes=[
            {'frame': 0, 'gainRgb': [.6, .5, .4]}, {'frame': 100, 'gainRgb': [.8, .55, .35]}])
        np.testing.assert_allclose(worker.gain_at_frame(definition, 0), [.6, .5, .4])
        np.testing.assert_allclose(worker.gain_at_frame(definition, 50), [.7, .525, .375])
        np.testing.assert_allclose(worker.gain_at_frame(definition, 100), [.8, .55, .35])
        self.assertLess(np.linalg.norm(worker.gain_at_frame(definition, 1)
            - worker.gain_at_frame(definition, 0)), .001)

    def test_inert_template_lighting_does_not_change_surrounding_pixels(self):
        definition = dict(self.definition, gainRgbKeyframes=[
            {'frame': 0, 'gainRgb': [.6, .5, .4]}, {'frame': 100, 'gainRgb': [.3, .25, .2]}])
        texture = np.full((4, 4, 3), 100.0)
        face = np.zeros_like(texture)
        face[1:3, 1:3] = 40
        output = worker.texture_at_frame({'definition': definition, 'texture': texture,
            'nativeFaceContribution': face}, 100)
        np.testing.assert_array_equal(output[0], texture[0])
        np.testing.assert_array_equal(output[1:3, 1:3], np.full((2, 2, 3), 80))

    def test_rejects_a_curve_that_disagrees_with_its_first_frame(self):
        with self.assertRaisesRegex(ValueError, 'Ordered finite lighting keyframes'):
            worker.gain_at_frame(dict(self.definition, gainRgbKeyframes=[
                {'frame': 0, 'gainRgb': [.8, .5, .4]}, {'frame': 100, 'gainRgb': [.8, .55, .35]}]), 0)


if __name__ == '__main__':
    unittest.main()
