"""Verify the displacement coordinate system independently of video aesthetics."""
import unittest
import numpy as np
from measure_prop_motion import relative_point


class RelativePropMotionTest(unittest.TestCase):
    def test_camera_motion_alone_is_cancelled(self):
        camera=np.array([[1.1,0,12],[0,1.1,-5],[0,0,1]])
        np.testing.assert_allclose(relative_point(camera,camera,[700,350]),[0,0],atol=1e-10)

    def test_left_translation_remains_under_camera_transform(self):
        camera=np.array([[1.1,0,12],[0,1.1,-5],[0,0,1]])
        move=np.array([[1,0,-90],[0,1,0],[0,0,1]])
        np.testing.assert_allclose(relative_point(camera@move,camera,[700,350]),[-90,0],atol=1e-10)

    def test_vertical_bob_does_not_become_horizontal_translation(self):
        bounce=np.array([[1,0,0],[0,1,-30],[0,0,1]])
        np.testing.assert_allclose(relative_point(bounce,np.eye(3),[700,350]),[0,-30],atol=1e-10)


if __name__=='__main__':
    unittest.main()
