# SPDX-License-Identifier: GPL-3.0-only
import os,subprocess,tempfile,unittest
from pathlib import Path
B=Path(__file__).resolve().parent
class Tests(unittest.TestCase):
 def call(self,mode):
  with tempfile.TemporaryDirectory() as d:
   snap=str(Path(d)/'format.bin');env=dict(os.environ,MOCK_STATE_MODE='readonly',LD_PRELOAD=str(B/'mock_camera_state.so'))
   saved=subprocess.run([str(B/'camera-state'), 'save','/dev/null',snap,'0'],capture_output=True,env=env)
   self.assertEqual(saved.returncode,0,saved.stderr)
   env['MOCK_STATE_MODE']=mode
   return subprocess.run([str(B/'camera-state'),'restore','/dev/null',snap,'0'],capture_output=True,env=env)
 def test_readonly_crop_exactly_restored(self):self.assertEqual(self.call('readonly').returncode,0)
 def test_writable_crop_still_works(self):self.assertEqual(self.call('writable').returncode,0)
 def test_no_io_or_changed_crop_error_is_hidden(self):
  for mode in ['format-error','selection-error','readback-error','mismatch']:
   with self.subTest(mode=mode):self.assertNotEqual(self.call(mode).returncode,0)
if __name__=='__main__':unittest.main()
