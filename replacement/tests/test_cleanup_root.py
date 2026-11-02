# SPDX-License-Identifier: GPL-3.0-only
import os,unittest,uuid,json,hashlib,types,shutil
from pathlib import Path
from cleanup_contract import cleanup
@unittest.skipUnless(os.geteuid()==0,'Isolated VM root only')
class Tests(unittest.TestCase):
 def setUp(self):
  self.p=Path('/run')/('sp7-ir-metadata-'+uuid.uuid4().hex);self.p.mkdir(mode=0o700);self.addCleanup(lambda:shutil.rmtree(self.p) if self.p.exists() else None)
  self.expected={}
  for name in ['ir.raw','rgb.raw']+[f'format-{i}.bin' for i in range(24)]:
   data=('synthetic-'+name).encode();f=self.p/name;f.write_bytes(data);f.chmod(0o600 if name.endswith('.raw') else 0o644);owner=1000 if name.endswith('.raw') else 0;os.chown(f,owner,owner)
   self.expected[name]=dict(size=len(data),sha256=hashlib.sha256(data).hexdigest(),uid=owner,fsynced_backup=True)
  self.io=types.SimpleNamespace(guard=lambda:None,full_idle=lambda:{'complete':True},before_unlink=lambda p:None)
 def test_exact_backed_up_session_removed_without_capture(self):
  r=cleanup(self.p,self.expected,self.io);self.assertTrue(r['complete'],r);self.assertEqual(len(r['removed']),26);self.assertFalse(self.p.exists());self.assertFalse(r['capture_authorized'])
 def test_successful_teardown_profile_allows_only_two_exact_raw_files(self):
  for i in range(24):(self.p/f'format-{i}.bin').unlink()
  expected={k:v for k,v in self.expected.items() if k.endswith('.raw')}
  r=cleanup(self.p,expected,self.io,profile='raw_after_verified_teardown');self.assertTrue(r['complete'],r);self.assertEqual(len(r['removed']),2)
 def test_profile_cannot_hide_unknown_files_or_invent_a_generic_delete(self):
  expected={k:v for k,v in self.expected.items() if k.endswith('.raw')}
  for profile in ['raw_after_verified_teardown','any']:
   r=cleanup(self.p,expected,self.io,profile=profile);self.assertFalse(r['complete']);self.assertEqual(r['removed'],[])
 def test_corruption_unknown_file_or_missing_ack_delete_nothing(self):
  for mode in ['hash','extra','ack']:
   if mode=='hash':self.expected['ir.raw']['sha256']='0'*64
   if mode=='extra':(self.p/'foreign').write_text('retain')
   if mode=='ack':self.expected['rgb.raw']['fsynced_backup']=False
   r=cleanup(self.p,self.expected,self.io);self.assertFalse(r['complete']);self.assertEqual(r['removed'],[])
   if mode=='hash':self.expected['ir.raw']['sha256']=hashlib.sha256((self.p/'ir.raw').read_bytes()).hexdigest()
   if mode=='extra':(self.p/'foreign').unlink()
 def test_raw_or_metadata_write_permissions_are_not_relaxed(self):
  for name,mode in [('ir.raw',0o644),('format-0.bin',0o666)]:
   f=self.p/name;before=f.stat().st_mode&0o777;f.chmod(mode);r=cleanup(self.p,self.expected,self.io);self.assertFalse(r['complete']);self.assertEqual(r['removed'],[]);f.chmod(before)
 def test_symlink_cannot_be_followed_or_removed(self):
  f=self.p/'ir.raw';f.unlink();f.symlink_to('/etc/passwd');r=cleanup(self.p,self.expected,self.io);self.assertFalse(r['complete']);self.assertEqual(r['removed'],[]);self.assertTrue(f.is_symlink())
 def test_replacement_after_verification_is_not_unlinked(self):
  def mutate(path):path.write_text('changed')
  self.io.before_unlink=mutate;r=cleanup(self.p,self.expected,self.io);self.assertFalse(r['complete']);self.assertEqual(r['removed'],[])
 def test_unknown_idle_prevents_any_removal(self):
  def refuse():raise ValueError('Unknown idle')
  self.io.full_idle=refuse;r=cleanup(self.p,self.expected,self.io);self.assertFalse(r['complete']);self.assertEqual(r['removed'],[])
if __name__=='__main__':unittest.main()
