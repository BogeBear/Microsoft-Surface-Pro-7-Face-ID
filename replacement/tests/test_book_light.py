# SPDX-License-Identifier: GPL-3.0-only
import unittest
from book_light import arm,raw,ADDRESSES,verify_receipts
class IO:
    def __init__(self,mode='normal'):self.t=1_000_000;self.on=False;self.calls=[];self.mode=mode
    def now_ns(self):self.t+=1000;return self.t
    def guard(self):
        self.calls.append('guard')
        if self.mode=='thermal':raise ValueError('Thermal')
    def status(self):
        on=int(self.on)
        if self.mode=='malformed':return 'invalid'
        return f'schema=sp7-independent-v1 stream=1 power_held=1 armed={on} pending={on} fault=0 error=0 consumed={on} remaining_ns={2_900_000_000 if on else 0}'
    def snapshot(self):
        x={a:0 for a in ADDRESSES};x[0x0100]=1;x[0x3b96]=0x40
        if self.on:x[0x3005]|=8;x[0x3b80]|=16;x[0x3b96]|=128
        if self.mode=='pulse_changed' and self.on:x[0x3b8f]=255
        return 'schema=sp7-independent-raw-v1 '+' '.join(f'{a:04x}={v:02x}' for a,v in x.items())
    def workers_alive(self):return True
    def sleep(self,s):self.t+=int(s*1e9)
    def capture(self):self.calls.append('capture');self.on=True
class Tests(unittest.TestCase):
    def test_one_running_three_gate_enable_with_full_raw_preservation(self):
        io=IO();r=arm(io);self.assertEqual(io.calls.count('capture'),1);self.assertFalse(r['optical_emission_verified']);self.assertEqual(raw(r['enabled_raw'])['3b96'],0xc0)
    def test_thermal_unknown_or_unrelated_register_change_is_rejected(self):
        for mode in ['thermal','malformed','pulse_changed']:
            with self.subTest(mode=mode),self.assertRaises(ValueError):arm(IO(mode))
    def test_raw_inventory_cannot_drop_duplicate_or_add_registers(self):
        for text in [IO().snapshot().replace('3b96=40','ffff=40'),IO().snapshot()+' 0100=01',IO().snapshot().replace(' 3503=00','')]:
            with self.assertRaises(ValueError):raw(text)
    def receipts(self):
        io=IO();a=arm(io);return dict(running_light_arm=a,post_native_control='schema=sp7-independent-v1 stream=0 power_held=0 armed=0 pending=0 fault=0 error=0 consumed=1 remaining_ns=0',post_native_dark=dict(light_off_verified=True,after='armed=0 remaining_ms=0 cleanup_pending=0 recovery_required=0'),post_native_dark_ns=a['end_ns']+1_000_000_000)
    def test_complete_light_receipts_are_separate_from_optical_proof(self):
        r=verify_receipts(self.receipts());self.assertTrue(r['three_gate_enable_readbacks_verified']);self.assertFalse(r['optical_emission_verified'])
    def test_expired_unknown_owned_or_unclosed_is_not_shutdown(self):
        for change in ['running','fault','off','time']:
            m=self.receipts()
            if change=='running':m['post_native_control']=m['post_native_control'].replace('stream=0 power_held=0','stream=1 power_held=1')
            if change=='fault':m['post_native_control']=m['post_native_control'].replace('fault=0 error=0','fault=1 error=-5')
            if change=='off':m['post_native_dark']['light_off_verified']=False
            if change=='time':m['post_native_dark_ns']=m['running_light_arm']['begin_ns']+3_200_000_000
            with self.subTest(change=change),self.assertRaises(ValueError):verify_receipts(m)
if __name__=='__main__':unittest.main()
