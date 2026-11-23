"""Carrier tracking must ignore independently animated ink. GPL-3.0-only."""
import unittest
import cv2
import numpy as np
from stabilize_carrier_plane import CarrierTracker, polygon_mask


class CarrierPlaneTest(unittest.TestCase):
    def test_carrier_transform_ignores_changed_print(self):
        random = np.random.default_rng(43)
        first = random.integers(20, 210, (240, 360, 3), dtype=np.uint8)
        first = cv2.GaussianBlur(first, (3, 3), 0)
        print_region = [[120, 60], [230, 60], [230, 190], [120, 190]]
        carrier = [[[20, 20], [340, 20], [340, 220], [20, 220]]]
        tracker = CarrierTracker(first, carrier, [print_region])
        matrix = cv2.getRotationMatrix2D((180, 120), 1.2, 1.01)
        matrix[:, 2] += [4, -3]
        moved = cv2.warpAffine(first, matrix, (360, 240))
        cv2.rectangle(moved, (120, 60), (235, 195), (0, 0, 255), -1)
        actual, metric = tracker.transform(moved)
        points = np.float32([[[40, 40], [300, 200], [180, 120]]])
        expected = cv2.transform(points, matrix)
        found = cv2.perspectiveTransform(points, actual)
        self.assertLess(float(np.linalg.norm(found-expected, axis=2).max()), .3)
        self.assertGreater(metric['inliers'], 20)

    def test_missing_carrier_fails(self):
        with self.assertRaisesRegex(ValueError, 'insufficient'):
            CarrierTracker(np.zeros((100, 100, 3), np.uint8), [[[1, 1], [98, 1], [98, 98], [1, 98]]])

    def test_mask_cannot_escape_frame(self):
        with self.assertRaisesRegex(ValueError, 'escaped'):
            polygon_mask((100, 100, 3), [[[-1, 2], [30, 3], [30, 40]]])


if __name__ == '__main__':
    unittest.main()
