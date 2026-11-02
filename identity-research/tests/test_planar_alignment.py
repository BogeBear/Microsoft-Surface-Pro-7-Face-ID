# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
import numpy as np
from planar_alignment import fit_points,gray,register,validate_fixed


class Tests(unittest.TestCase):
    def points(self):
        x,y=np.meshgrid(np.linspace(.1,.9,6),np.linspace(.1,.9,5))
        return np.column_stack([x.ravel(),y.ravel()])
    def test_synthetic_projective_plane_with_outliers(self):
        import cv2
        s=self.points();H=np.array([[.7,.03,.1],[.02,.75,.1],[.05,.03,1.]])
        t=cv2.perspectiveTransform(s[None,:,:],H)[0]
        t[:4]=np.array([[.9,.1],[.2,.8],[.8,.2],[.3,.9]])
        m=fit_points(s,t)
        self.assertGreaterEqual(m['inliers'],26)
        self.assertLess(m['fitted_inlier_p95_normalized_error'],1e-5)
        self.assertFalse(m['biometric_calibration_verified'])
    def test_mirrored_plane_not_confused_with_depth(self):
        s=self.points();t=s.copy();t[:,0]=1-t[:,0]
        m=fit_points(s,t)
        self.assertLess(np.linalg.det(np.array(m['H'])),0)
        self.assertFalse(m['depth_verified']);self.assertFalse(m['authentication_allowed'])
    def test_insufficient_clustered_collinear_nonfinite_refused(self):
        s=self.points()
        for x in (s[:5],s*.01,np.column_stack([s[:,0],s[:,0]]),s*np.nan,s+2):
            with self.subTest(shape=x.shape):
                with self.assertRaises(ValueError):fit_points(x,x)
    def test_blank_images_refuse_both_hypotheses(self):
        r=register(np.zeros((128,128),np.uint8),np.zeros((128,128),np.uint8))
        self.assertTrue(all(not x['accepted'] for x in r['candidates']))
    def test_layout_and_size_budget(self):
        for x in (np.zeros((8,8),np.uint8),np.zeros((64,64,4),np.uint8),np.zeros((64,64),np.uint16)):
            with self.assertRaises(ValueError):gray(x)
    def test_fixed_model_requires_explicit_valid_inputs(self):
        x=np.zeros((128,128),np.uint8)
        with self.assertRaises(ValueError):validate_fixed(x,x,np.eye(3),1)
        with self.assertRaises(ValueError):validate_fixed(x,x,np.zeros((2,3)),False)
        r=validate_fixed(x,x,np.eye(3),False)
        self.assertEqual(r['matches'],0);self.assertFalse(r['model_refitted'])


if __name__=='__main__':unittest.main()
