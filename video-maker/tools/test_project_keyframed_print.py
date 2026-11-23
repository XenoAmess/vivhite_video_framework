"""Carrier annotation bounds and orientation must remain valid. GPL-3.0-only."""
import unittest
import numpy as np
from project_keyframed_print import quad_at


class KeyframedCarrierTest(unittest.TestCase):
    def setUp(self):
        self.keys = [{'frame':0,'quad':[[10,10],[110,10],[110,90],[10,90]]},
                     {'frame':10,'quad':[[30,20],[150,20],[150,120],[30,120]]}]

    def test_exact_observed_anchors_and_intermediate_plane(self):
        np.testing.assert_allclose(quad_at(self.keys,0), self.keys[0]['quad'])
        np.testing.assert_allclose(quad_at(self.keys,10), self.keys[1]['quad'])
        np.testing.assert_allclose(quad_at(self.keys,5), [[20,15],[130,15],[130,105],[20,105]])

    def test_cannot_extrapolate_beyond_observed_video(self):
        with self.assertRaisesRegex(ValueError,'bounded'):
            quad_at(self.keys,11)

    def test_reflected_or_crossed_carrier_is_rejected(self):
        reflected = [{'frame':0,'quad':self.keys[0]['quad'][::-1]}]
        with self.assertRaisesRegex(ValueError,'reflection'):
            quad_at(reflected,0)
        crossed = [{'frame':0,'quad':[[10,10],[110,90],[110,10],[10,90]]}]
        with self.assertRaisesRegex(ValueError,'nonconvex'):
            quad_at(crossed,0)


if __name__ == '__main__':
    unittest.main()
