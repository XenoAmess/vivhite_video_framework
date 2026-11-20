"""Check actual eye-only registration gap and invalid face mappings."""
from pathlib import Path
import importlib.util
import unittest

import numpy as np

MODULE = Path(__file__).with_name('restore-S40-three-point-print-v12.py')
spec = importlib.util.spec_from_file_location('s40_face_registration', MODULE)
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


class FaceRegistrationTest(unittest.TestCase):
    def definition(self):
        return {'registrationMode': 'three-point-affine-face',
            'referenceLandmarks': [[457, 554], [681, 529], [585, 692]],
            'targetLandmarks': [[2547, 1046], [2656, 1029], [2607, 1126]],
            'referenceEyes': [457, 554, 681, 529], 'targetEyes': [2547, 1046, 2656, 1029]}

    def test_actual_chin_gap_is_closed_without_moving_the_two_eyes(self):
        from restore_printed_eyes import eye_registration
        definition = self.definition()
        before = np.asarray(definition['referenceLandmarks'])
        after = np.asarray(definition['targetLandmarks'])
        old = eye_registration(definition['referenceEyes'], definition['targetEyes'])
        old_chin = old @ np.r_[before[2], 1]
        self.assertGreater(np.linalg.norm(old_chin - after[2]), 15)
        actual = worker.face_registration(definition)
        np.testing.assert_allclose(before @ actual[:, :2].T + actual[:, 2], after, atol=.01)

    def test_reflection_and_collinear_landmarks_are_rejected(self):
        for point in ([2607, 900], [2765, 1012]):
            with self.subTest(point=point):
                definition = self.definition()
                definition['targetLandmarks'][2] = point
                with self.assertRaises(ValueError):
                    worker.face_registration(definition)

    def test_nonfinite_or_mismatched_eye_anchors_are_rejected(self):
        for point in ([float('nan'), 1126], [2607, float('inf')]):
            definition = self.definition()
            definition['targetLandmarks'][2] = point
            with self.assertRaises(ValueError):
                worker.face_registration(definition)
        definition = self.definition()
        definition['targetEyes'][0] += 1
        with self.assertRaises(ValueError):
            worker.face_registration(definition)


if __name__ == '__main__':
    unittest.main()
