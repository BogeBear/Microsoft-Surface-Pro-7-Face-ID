import errno,io,json,unittest,types
from unittest.mock import patch
import inspector as s
from test_inspector import FakeSystem
from stable_idle import full_idle
class ReadPolicy(unittest.TestCase):
 def fail(self,path,error):
  with patch('builtins.open',side_effect=error):return s.System().read(path)
 def test_exact_proc_task_stat_ESRCH_is_transient(self):
  with self.assertRaisesRegex(s.SnapshotChanged,'task_exited_during_proc_stat:'):
   self.fail('/proc/706/task/7857/stat',ProcessLookupError(errno.ESRCH,'gone'))
 def test_ESRCH_on_other_paths_remains_unknown(self):
  for p in ['/proc/706/task/7857/fd/4','/proc/706/task/7857/map_files','/proc/706/stat','/proc/0/task/1/stat','/proc/706/task/abc/stat','/sys/class/hwmon/hwmon5/temp1_input']:
   with self.assertRaises(s.Unknown) as cm:self.fail(p,ProcessLookupError(errno.ESRCH,'gone'))
   self.assertNotIsInstance(cm.exception,s.SnapshotChanged)
 def test_permission_IO_and_invalid_errors_never_retry(self):
  for code in [errno.EACCES,errno.EIO,errno.EINVAL]:
   with self.assertRaises(s.Unknown) as cm:self.fail('/proc/706/task/7857/stat',OSError(code,'denied'))
   self.assertNotIsInstance(cm.exception,s.SnapshotChanged)
 def test_error_during_opened_file_read_is_also_classified(self):
  class Stream(io.StringIO):
   def read(self,*a):raise ProcessLookupError(errno.ESRCH,'thread ended after open')
  with patch('builtins.open',return_value=Stream()):
   with self.assertRaises(s.SnapshotChanged):s.System().read('/proc/706/task/7857/stat')
class WholeScan(unittest.TestCase):
 def make(self,camera=False,persistent=False):
  fs=FakeSystem();original=fs.read;state=dict(events=0)
  if camera:fs.metadata['/proc/10/task/10/fd/0']=fs.camera()
  def read(path):
   if path=='/proc/10/task/11/stat' and (persistent or state['events']==0):
    state['events']+=1
    if not persistent:fs.directories['/proc/10/task'].remove('11')
    raise s.SnapshotChanged('task_exited_during_proc_stat:'+path)
   return original(path)
  fs.read=read;return fs,state
 def test_exit_requires_two_new_complete_passes(self):
  fs,events=self.make();r=s.collect(fs,99,lambda:100.);self.assertTrue(r['complete']);self.assertEqual(r['passes'],2);self.assertEqual(r['whole_scan_rechecks'],1);self.assertEqual(r['passes_started'],3);self.assertEqual(r['tasks_checked'],2);self.assertEqual(events['events'],1)
 def test_observed_camera_is_never_forgotten(self):
  fs,_=self.make(camera=True)
  with self.assertRaisesRegex(s.Unknown,'camera_seen_during_unstable_process'):s.collect(fs,99,lambda:100.)
 def test_persistent_exit_stops_at_internal_limit(self):
  fs,events=self.make(persistent=True)
  with self.assertRaisesRegex(s.Unknown,'unstable_process_inventory_after_2_attempts:task_exited_during_proc_stat:'):s.collect(fs,99,lambda:100.)
  self.assertEqual(events['events'],2)
 def test_persistent_exit_stops_after_three_external_reads(self):
  calls=[]
  def once(timeout):
   fs,_=self.make(persistent=True)
   try:s.collect(fs,99,lambda:100.)
   except s.Unknown as e:q=dict(exit=2,stdout=json.dumps(dict(complete=False,reason=str(e))),stderr='')
   return q
  x=types.SimpleNamespace(bind=lambda:None,cool=lambda:None,inspect_once=once,record_idle_attempt=calls.append,validate=lambda _:self.fail('No validation allowed'))
  with self.assertRaisesRegex(RuntimeError,'three bounded reads'):full_idle(x,lambda:100.,lambda _:None)
  self.assertEqual(len(calls),3)
 def test_camera_plus_exit_never_gets_an_external_retry(self):
  calls=[]
  def once(timeout):
   fs,_=self.make(camera=True)
   try:s.collect(fs,99,lambda:100.)
   except s.Unknown as e:return dict(exit=2,stdout=json.dumps(dict(complete=False,reason=str(e))),stderr='')
  x=types.SimpleNamespace(bind=lambda:None,cool=lambda:None,inspect_once=once,record_idle_attempt=calls.append,validate=lambda _:self.fail('Camera disappeared from proof'))
  with self.assertRaisesRegex(RuntimeError,'camera_seen'):full_idle(x,lambda:100.,lambda _:None)
  self.assertEqual(len(calls),1)
if __name__=='__main__':unittest.main()
