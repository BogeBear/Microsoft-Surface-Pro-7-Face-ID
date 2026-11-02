# SPDX-License-Identifier: GPL-3.0-only
import unittest
import presence as p
class Tests(unittest.TestCase):
 def test_left_message_and_ready_label(self):
  title,body,button,on=p.presentation(dict(phase='awaiting_presence',capture_index=1));self.assertIn('your left',title);self.assertIn('Keep the SP7 in place',body);self.assertIn('left',button);self.assertTrue(on)
 def test_right_message_and_ready_label(self):
  title,body,button,on=p.presentation(dict(phase='awaiting_presence',capture_index=2));self.assertIn('your right',title);self.assertIn('Keep the SP7 in place',body);self.assertIn('right',button);self.assertTrue(on)
 def test_missing_pose_does_not_enable_ready(self):self.assertFalse(p.presentation(dict(phase='awaiting_presence'))[3])
 def test_left_completion_requests_right_next(self):self.assertIn('right',p.presentation(dict(phase='finished',safe_to_leave=True,capture_index=1))[1])
