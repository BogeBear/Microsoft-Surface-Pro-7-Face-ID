# SPDX-License-Identifier: GPL-3.0-only
import unittest
from independent_status import parse
S='schema=sp7-independent-v1 stream=0 power_held=0 armed=0 pending=0 fault=0 error=0 consumed=0 remaining_ns=0'
class Tests(unittest.TestCase):
 def test_clear_is_not_full_idle_or_authentication(self):
  r=parse(S);self.assertTrue(r['light_closure_fields_clear']);self.assertTrue(r['session_released']);self.assertFalse(r['full_idle_verified']);self.assertFalse(r['authentication_allowed'])
 def test_fault_and_pending_never_clear(self):
  r=parse(S.replace('pending=0','pending=1').replace('fault=0','fault=1').replace('error=0','error=-5'))
  self.assertFalse(r['light_closure_fields_clear'])
 def test_invalid_states(self):
  for t in [S+' armed=0',S.replace('stream=0','stream=2'),S.replace('error=0','error=-5000'),S.replace('remaining_ns=0','remaining_ns=3000000001'),S.replace('fault=0','fault=1'),S.replace('stream=0','stream=1'),S.replace('armed=0','armed=1'),S.replace('error=0','error=+0'),S.replace('stream=0','other=0'),S.replace('schema=sp7-independent-v1','schema=old'),S.replace(' consumed=0','')]:
   with self.subTest(status=t):
    with self.assertRaises(ValueError):parse(t)
 def test_expired_arm_is_not_clean(self):
  r=parse(S.replace('stream=0','stream=1').replace('power_held=0','power_held=1').replace('armed=0','armed=1').replace('pending=0','pending=1').replace('consumed=0','consumed=1'))
  self.assertFalse(r['light_closure_fields_clear']);self.assertFalse(r['session_released'])
if __name__=='__main__':unittest.main()
