# SPDX-License-Identifier: GPL-3.0-only
import unittest
import numpy as np
import image_pipeline as p
class Tests(unittest.TestCase):
 def test_window_geometry_and_no_alias(self):
  x=np.zeros((1944,2592,3),np.uint8);x[486,648]=[1,2,3];a,o=p.rgb_proposal_window(x);self.assertEqual(o,(648,486));self.assertEqual(a.shape,(972,1296,3));self.assertEqual(a[0,0].tolist(),[1,2,3]);a[:]=0;self.assertEqual(x[486,648].tolist(),[1,2,3])
 def test_raw_range_shape_type(self):
  for a in [np.zeros((480,640),np.float32),np.zeros((1,640),np.uint16),np.full((480,640),1024,np.uint16)]:
   with self.assertRaises(ValueError):p.raw_plane(a,(480,640))
 def test_window_invalid(self):
  for a in [np.zeros((1944,2592,3),np.float32),np.zeros((1944,2592),np.uint8)]:
   with self.assertRaises(ValueError):p.rgb_proposal_window(a)
 def test_color_invalid_before_conversion(self):
  a=np.zeros((1944,2592),np.uint16)
  for g,w in [([1,1],50),([float('nan'),1,1],50),([1,1,5],50),([1,1,1],True),([1,1,1],float('inf')),([1,1,1],0)]:
   with self.assertRaises(ValueError):p.rgb_image(a,g,w,cv=object())
 def test_mapping_preserves_fail_closed(self):
  r=dict(faces=[dict(box_xyxy=[10,20,30,40],score=.9)],authentication_allowed=False,password_required=True,PAD_verified=False)
  x=p.map_rgb_proposals(r,(648,486));self.assertEqual(x['faces'][0]['box_xyxy'],[658,506,678,526]);self.assertEqual(r['faces'][0]['box_xyxy'],[10,20,30,40]);self.assertFalse(x['authentication_allowed']);self.assertFalse(x['full_field_multiple_person_exclusion_verified']);self.assertFalse(x['geometric_RGB_IR_calibration_verified'])
 def test_invalid_contract_and_bounds(self):
  r=dict(faces=[],authentication_allowed=False,password_required=True,PAD_verified=False)
  for k in ['authentication_allowed','password_required','PAD_verified']:
   with self.assertRaises(ValueError):p.map_rgb_proposals(dict(r,**{k:not r[k]}),(648,486))
  with self.assertRaises(ValueError):p.map_rgb_proposals(r,(0,0))
  for b in [[0,0,1297,1],[0,0,1,973],[0,0,float('nan'),3],[1,1,0,2]]:
   with self.assertRaises(ValueError):p.map_rgb_proposals(dict(r,faces=[dict(box_xyxy=b)]),(648,486))
if __name__=='__main__':unittest.main()
