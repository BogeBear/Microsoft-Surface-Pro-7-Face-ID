# SPDX-License-Identifier: GPL-3.0-or-later
import unittest,numpy as np
from coordinate_profile import ir_preview,legacy_box_to_profile,legacy_points_to_profile,PROFILE_ID,PRODUCTION_ADOPTION


class Tests(unittest.TestCase):
    def test_full_plane_mirrored_once_without_mutating_base(self):
        image=np.zeros((640,480,3),np.uint8);image[:,0]=9;image[:,-1]=13
        called=[]
        def base(raw,filtered):called.append(filtered);return image
        out=ir_preview(None,base=base)
        self.assertEqual(called,[True]);self.assertTrue(out.flags.c_contiguous)
        self.assertTrue((out[:,0]==13).all());self.assertTrue((out[:,-1]==9).all())
        self.assertTrue((image[:,0]==9).all());self.assertFalse(np.shares_memory(out,image))
    def test_half_open_box_edges_roundtrip(self):
        for box in ([0,0,480,640],[1.,2.,79.,90.],[400,20,479,580]):
            self.assertEqual(legacy_box_to_profile(legacy_box_to_profile(box)),list(box))
    def test_invalid_box_rejected(self):
        for box in ([0,0,0,640],[-1,0,2,3],[0,0,481,4],[0,0,float('nan'),4],[False,0,1,2]):
            with self.assertRaises(ValueError):legacy_box_to_profile(box)
    def test_profile_cannot_activate_production(self):
        self.assertEqual(PROFILE_ID,'sp7-research-ir-mirror-x-v1');self.assertIs(PRODUCTION_ADOPTION,False)
    def test_wrong_base_layout_rejected(self):
        with self.assertRaises(ValueError):ir_preview(None,base=lambda *a,**k:np.zeros((480,640,3),np.uint8))
    def test_subpixel_centres_use_pixel_not_box_convention(self):
        p=np.array([[0.,0.],[479.,639.],[123.25,243.75]])
        np.testing.assert_array_equal(legacy_points_to_profile(p),[[479.,0.],[0.,639.],[355.75,243.75]])
        np.testing.assert_array_equal(legacy_points_to_profile(legacy_points_to_profile(p)),p)
    def test_invalid_subpixel_geometry_rejected(self):
        for p in ([],[[480.,1.]],[[0.,640.]],[[float('nan'),0.]],[[1,2,3]]):
            with self.assertRaises(ValueError):legacy_points_to_profile(p)


if __name__=='__main__':unittest.main()
