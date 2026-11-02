import unittest
import inspector as s
from test_inspector import FakeSystem
class Tests(unittest.TestCase):
 def fixture(self,persistent=False,camera_before=False,camera_during=False):
  fs=FakeSystem();base=fs.names;state={'calls':0}
  if camera_before:fs.metadata['/proc/10/task/10/fd/0']=fs.camera()
  if camera_during:fs.metadata['/proc/10/task/11/fd/7']=fs.camera()
  def names(path):
   if path=='/proc/10/task/11/fd':
    state['calls']+=1
    if (persistent or state['calls']<=6) and state['calls']%2==0:return ['7','8']
   return base(path)
  fs.names=names;return fs,state
 def test_local_exhaustion_requires_two_new_complete_passes(self):
  fs,c=self.fixture();r=s.collect(fs,99,lambda:100.);self.assertTrue(r['complete']);self.assertEqual(r['whole_scan_rechecks'],1);self.assertEqual(r['passes_started'],3);self.assertEqual(r['passes'],2);self.assertEqual(r['camera_holders'],[]);self.assertGreater(c['calls'],6)
 def test_persistent_churn_stops_at_existing_whole_limit(self):
  fs,c=self.fixture(True)
  with self.assertRaisesRegex(s.Unknown,'unstable_process_inventory_after_2_attempts:thread_inventory_unstable_after_3_attempts'):s.collect(fs,99,lambda:100.)
  self.assertEqual(c['calls'],12)
 def test_camera_in_previous_task_is_not_forgotten(self):
  fs,c=self.fixture(camera_before=True)
  with self.assertRaisesRegex(s.Unknown,'camera_seen_during_unstable_process_inventory'):s.collect(fs,99,lambda:100.)
  self.assertEqual(c['calls'],6)
 def test_camera_in_current_discarded_attempt_is_not_forgotten(self):
  fs,c=self.fixture(camera_during=True)
  with self.assertRaisesRegex(s.Unknown,'camera_seen_during_unstable_inventory'):s.collect(fs,99,lambda:100.)
  self.assertEqual(c['calls'],2)
 def test_permission_failure_is_not_retried(self):
  fs,c=self.fixture();fs.deny='/proc/10/task/11/fd/7'
  with self.assertRaises(PermissionError):s.collect(fs,99,lambda:100.)
  self.assertEqual(c['calls'],1)
 def test_reuse_failure_is_not_retried(self):
  fs,c=self.fixture();base=fs.read;calls=0
  def read(path):
   nonlocal calls
   if path=='/proc/10/task/11/stat':
    calls+=1
    if calls>1:return base(path).replace('1234','9999')
   return base(path)
  fs.read=read
  with self.assertRaisesRegex(s.Unknown,'task_reused'):s.collect(fs,99,lambda:100.)
 def test_clock_budget_remains_four_seconds(self):
  fs,c=self.fixture();value=[100.]
  def clock():value[0]+=.25;return value[0]
  with self.assertRaisesRegex(s.Unknown,'deadline'):s.collect(fs,99,clock)
if __name__=='__main__':unittest.main()
