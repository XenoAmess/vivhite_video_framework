import unittest

import numpy as np

from restore_printed_badge_lighting import prepare


class BadgeLightingTest(unittest.TestCase):
    def setUp(self):
        self.raw = np.random.default_rng(3).integers(0, 255, (200, 240, 3), dtype=np.uint8)
        self.reference = np.full((100, 100, 4), (180, 200, 240, 255), dtype=np.uint8)
        self.configuration = {'gainRgb': [.7, .8, .9], 'referenceSofteningSigma': 0,
            'center': [120, 100], 'radius': 40, 'maximumTrackedScale': 2.5,
            'referenceBox': [0, 0, 100, 100], 'targetBox': [70, 50, 170, 150]}

    def test_colored_projection_preserves_unmasked_scene_and_inputs(self):
        raw_before, reference_before = self.raw.copy(), self.reference.copy()
        tracker, result = prepare(self.raw, self.reference, self.configuration)
        np.testing.assert_array_equal(result[tracker.mask == 0], self.raw[tracker.mask == 0])
        np.testing.assert_array_equal(result[100, 120], [162, 160, 168])
        np.testing.assert_array_equal(self.raw, raw_before)
        np.testing.assert_array_equal(self.reference, reference_before)

    def test_rejects_brightening_and_incomplete_projection(self):
        with self.assertRaises(ValueError):
            prepare(self.raw, self.reference, {**self.configuration, 'gainRgb': [1.2, .8, .9]})
        with self.assertRaises(ValueError):
            prepare(self.raw, self.reference, {**self.configuration, 'targetBox': [100, 80, 140, 120]})


if __name__ == '__main__':
    unittest.main()
