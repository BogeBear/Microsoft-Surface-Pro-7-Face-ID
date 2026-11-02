# SPDX-License-Identifier: GPL-3.0-only
import unittest,tempfile,json,hashlib,os
from pathlib import Path
from unittest.mock import patch
import ram_stage as m
class Tests(unittest.TestCase):
 def setUp(self):
  if os.geteuid()!=0:self.skipTest('Real root execution is tested in the isolated VM')
  self.t=tempfile.TemporaryDirectory(dir='/root');self.addCleanup(self.t.cleanup);self.p=Path(self.t.name)
  self.boot=self.p/'boot';self.boot.write_text('boot-a')
  self.cp=self.p/'checkpoint';self.cp.write_text(json.dumps({'boot_id':'boot-a','active':False}))
  self.args=dict(boot_path=self.boot,expected_boot='boot-a',checkpoint=self.cp,expected_checkpoint=hashlib.sha256(self.cp.read_bytes()).hexdigest())
  self.files={n:b'fixture' for n in m.NAMES};self.dest=self.p/'new'
 def test_stage_ownership_modes_and_no_overwrite(self):
  r=m.stage(self.files,self.dest,**self.args);self.assertTrue(r['staged']);self.assertFalse(r['modules_loaded'])
  self.assertEqual({x.name for x in self.dest.iterdir()},m.NAMES|{'manifest.json','receipt.json'})
  self.assertEqual(self.dest.stat().st_mode&0o777,0o755)
  for x in self.dest.iterdir():self.assertEqual(x.stat().st_uid,0);self.assertEqual(x.stat().st_mode&0o777,0o755 if x.name in ('helper','inspect') else 0o444)
  with self.assertRaises(FileExistsError):m.stage(self.files,self.dest,**self.args)
 def test_boot_or_checkpoint_change_no_writes(self):
  for key,value in [('expected_boot','other'),('expected_checkpoint','f'*64)]:
   args=dict(self.args,**{key:value})
   with self.assertRaises(ValueError):m.stage(self.files,self.dest,**args)
   self.assertFalse(self.dest.exists())
 def test_hold_is_not_cleared_by_staging(self):
  self.cp.write_text(json.dumps({'boot_id':'boot-a','active':False,'camera_operation_hold':{'active':True}}))
  self.args['expected_checkpoint']=hashlib.sha256(self.cp.read_bytes()).hexdigest()
  with self.assertRaises(ValueError):m.stage(self.files,self.dest,**self.args)
  self.assertFalse(self.dest.exists())
 def test_inventory_and_symlink_denied(self):
  files=dict(self.files);files['../escape']=b'fixture'
  with self.assertRaises(ValueError):m.stage(files,self.dest,**self.args)
  self.dest.symlink_to(self.p,target_is_directory=True)
  with self.assertRaises(FileExistsError):m.stage(self.files,self.dest,**self.args)
 def test_bound_inactive_restoration_material_preserves_hold(self):
  c={'boot_id':'boot-a','active':False,'phase':'independent_pre_capture_restoration_hold','camera_operation_hold':{'active':True,'failed_session':'a'*32}}
  self.cp.write_text(json.dumps(c));self.args['expected_checkpoint']=hashlib.sha256(self.cp.read_bytes()).hexdigest();before=self.cp.read_bytes()
  with self.assertRaises(ValueError):m.stage(self.files,self.dest,purpose='restoration_material',restoration_session='b'*32,**self.args)
  result=m.stage(self.files,self.dest,purpose='restoration_material',restoration_session='a'*32,**self.args)
  self.assertTrue(result['staged']);self.assertFalse(result['modules_loaded']);self.assertEqual(self.cp.read_bytes(),before)
  receipt=json.loads((self.dest/'receipt.json').read_text());self.assertFalse(receipt['capture_authorized']);self.assertTrue(receipt['camera_hold_preserved'])
 def test_post_capture_restoration_staging_never_authorizes_capture(self):
  c={'boot_id':'boot-a','active':False,'phase':'independent_post_capture_controls_restoration_hold','camera_operation_hold':{'active':True,'failed_session':'a'*32}}
  self.cp.write_text(json.dumps(c));self.args['expected_checkpoint']=hashlib.sha256(self.cp.read_bytes()).hexdigest();before=self.cp.read_bytes()
  with self.assertRaises(ValueError):m.stage(self.files,self.dest,**self.args)
  result=m.stage(self.files,self.dest,purpose='restoration_material',restoration_session='a'*32,**self.args)
  self.assertTrue(result['staged']);self.assertFalse(result['modules_loaded']);self.assertEqual(self.cp.read_bytes(),before)
  receipt=json.loads((self.dest/'receipt.json').read_text());self.assertTrue(receipt['camera_hold_preserved']);self.assertFalse(receipt['capture_authorized'])
 def test_invalid_reviewed_policy_cannot_write_outside_destination(self):
  bad=set(m.NAMES)|{'../escape'}
  with patch.object(m,'NAMES',bad):
   with self.assertRaisesRegex(ValueError,'Invalid reviewed payload policy'):m.stage(dict(self.files,**{'../escape':b'x'}),self.dest,**self.args)
  self.assertFalse(self.dest.exists());self.assertFalse((self.p/'escape').exists())
 def test_persistent_filesystem_is_not_called_RAM(self):
  with patch.object(m,'ram_filesystem',return_value=False):
   with self.assertRaisesRegex(ValueError,'RAM-only'):m.stage(self.files,self.dest,**self.args)
  self.assertFalse(self.dest.exists())
 def test_untrusted_parent_is_rejected(self):
  self.p.chmod(0o777)
  try:
   with self.assertRaisesRegex(ValueError,'Unprotected staging ancestor'):m.stage(self.files,self.dest,**self.args)
   self.assertFalse(self.dest.exists())
  finally:self.p.chmod(0o700)
 def test_checkpoint_changes_mid_stage_cleanup_only_own_files(self):
  original=os.fsync;calls=[]
  def changed(fd):
   calls.append(fd)
   if len(calls)==1:self.cp.write_text('{}')
   return original(fd)
  with patch.object(m.os,'fsync',side_effect=changed):
   with self.assertRaises(ValueError):m.stage(self.files,self.dest,**self.args)
  self.assertFalse(self.dest.exists())
if __name__=='__main__':unittest.main()
