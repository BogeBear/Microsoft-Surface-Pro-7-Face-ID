# SPDX-License-Identifier: GPL-3.0-only
import unittest
from rebind_contract import rebind
class IO:
    def __init__(self,fail=None):self.calls=[];self.fail=fail
    def step(self,name):
        self.calls.append(name)
        if len(self.calls)==self.fail:raise RuntimeError('Injected '+name)
        return {'complete':True,'idle':True}
    def check_binding(self):return self.step('binding')
    def full_idle(self):return self.step('full_idle')
    def verify_preconditions(self):return self.step('preconditions')
    def unbind(self):return self.step('unbind')
    def verify_detached(self):return self.step('detached')
    def bind_device(self):return self.step('bind')
    def verify_original_settings(self):return self.step('originals')
class Tests(unittest.TestCase):
    def test_order_and_no_capture_authority(self):
        io=IO();r=rebind(io)
        self.assertTrue(r['verified']);self.assertFalse(r['capture_authorized'])
        self.assertEqual(io.calls,['binding','full_idle','preconditions','full_idle','binding','unbind','detached','bind','binding','originals','full_idle'])
    def test_every_failed_boundary_stops_and_remains_unverified(self):
        for fail in range(1,12):
            with self.subTest(fail=fail):
                io=IO(fail);r=rebind(io)
                self.assertFalse(r['verified']);self.assertEqual(len(io.calls),fail)
                if fail<6:self.assertNotIn('unbind',io.calls)
                self.assertEqual(len(r['errors']),1)
    def test_final_settings_or_idle_cannot_be_replaced_by_prior_success(self):
        for fail in [10,11]:
            io=IO(fail);r=rebind(io)
            self.assertTrue(r['rebound']);self.assertFalse(r['verified'])
if __name__=='__main__':unittest.main()
