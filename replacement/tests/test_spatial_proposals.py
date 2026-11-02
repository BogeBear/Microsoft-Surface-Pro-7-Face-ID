# SPDX-License-Identifier: GPL-3.0-only
import unittest
import numpy as np
import spatial_proposals as s
class Detector:
 def __init__(self,rows):self.rows=iter(rows+([[]]*(9-len(rows))));self.calls=0
 def detect(self,x):
  self.calls+=1
  return dict(faces=next(self.rows),authentication_allowed=False,password_required=True,PAD_verified=False)
class Tests(unittest.TestCase):
 def setUp(self):self.im=np.zeros((1944,2592,3),np.uint8)
 def test_empty_requires_all_windows(self):
  d=Detector([[]]*5);r=s.collect(self.im,d);self.assertEqual(d.calls,9);self.assertTrue(r['all_windows_complete']);self.assertEqual(r['groups'],[]);self.assertFalse(r['authentication_allowed'])
 def test_offset_mapping_does_not_crop_other_windows(self):
  f=dict(box_xyxy=[10,20,30,40],score=.9);d=Detector([[],[f],[],[],[]]);r=s.collect(self.im,d);self.assertEqual(r['groups'][0]['box_xyxy'],[1306,20,1326,40]);self.assertFalse(r['full_field_multiple_person_exclusion_verified'])
 def test_duplicate_display_only_and_separate_people_remain_ambiguous(self):
  f=dict(box_xyxy=[700,500,800,600],score=.9);c=dict(box_xyxy=[52,14,152,114],score=.95);other=dict(box_xyxy=[10,20,100,200],score=.9)
  r=s.collect(self.im,Detector([[f],[other],[],[],[c]]));self.assertEqual(len(r['groups']),2);self.assertTrue(r['ambiguous_display_groups']);self.assertFalse(r['grouping_is_identity_matching']);self.assertTrue(r['password_required'])
 def test_error_in_late_view_never_returns_partial_success(self):
  class Fail(Detector):
   def detect(self,x):
    if self.calls==8:raise RuntimeError('thermal stop')
    return super().detect(x)
  with self.assertRaises(RuntimeError):s.collect(self.im,Fail([[]]*5))
 def test_top_middle_window_covers_centered_forehead(self):
  f=dict(box_xyxy=[10,20,30,40],score=.9);r=s.collect(self.im,Detector([[],[],[],[],[],[f]]));self.assertEqual(r['groups'][0]['box_xyxy'],[658,20,678,40]);self.assertEqual(r['views_checked'],9)
 def test_candidate_budget(self):
  with self.assertRaises(ValueError):s.collect(self.im,Detector([[dict(box_xyxy=[0,0,10,10],score=.9)]*65]))
 def test_invalid_input_and_out_of_window(self):
  with self.assertRaises(ValueError):s.collect(self.im[:10],Detector([[]]*5))
  with self.assertRaises(ValueError):s.collect(self.im,Detector([[dict(box_xyxy=[0,0,1297,1],score=.9)]]))
if __name__=='__main__':unittest.main()
