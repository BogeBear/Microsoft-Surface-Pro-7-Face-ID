# SPDX-License-Identifier: GPL-3.0-only
import unittest
from restore_contract import restore
class IO:
 def __init__(self,fail=None):self.events=[];self.fail=fail
 def action(self,name):
  self.events.append(name)
  if name==self.fail:raise RuntimeError('injected '+name)
 def bind_restore(self):self.action('bind')
 def full_idle(self):self.action('idle');return {'complete':True}
 def disconnect_original_trial_links(self):self.action('disconnect')
 def restore_format(self,n):self.action('restore'+str(n))
 def verify_format(self,n):self.action('verify'+str(n))
 def verify_controls(self,c):self.action('controls')
 def verify_graph(self,g):self.action('graph')
class Tests(unittest.TestCase):
 def original(self):return {'snapshots':[0,1,2],'sensor_controls':{},'graph':'original'}
 def test_order_and_no_capture_authority(self):
  io=IO();r=restore(io,self.original());self.assertTrue(r['restored']);self.assertFalse(r['capture_authorized']);self.assertTrue(r['root_exit_and_external_idle_required']);self.assertEqual(io.events.count('idle'),2)
  self.assertLess(io.events.index('idle'),io.events.index('disconnect'))
  for i in range(3):self.assertLess(io.events.index('restore2'),io.events.index('verify'+str(i)))
 def test_later_restore_cannot_hide_damage_to_an_earlier_record(self):
  io=IO();state={};base_restore=io.restore_format;base_verify=io.verify_format
  def write(n):
   base_restore(n);state[n]=True
   if n==2:state[0]=False
  def verify(n):
   base_verify(n)
   if not state.get(n):raise RuntimeError('cross-pad change')
  io.restore_format=write;io.verify_format=verify;r=restore(io,self.original());self.assertFalse(r['restored'])
 def test_initial_visibility_or_binding_failure_prevents_mutations(self):
  for fail in ['bind','idle']:
   io=IO(fail);r=restore(io,self.original());self.assertFalse(r['restored']);self.assertNotIn('disconnect',io.events)
 def test_each_restore_verify_or_complete_state_failure_blocks_completion(self):
  for fail in ['disconnect','restore0','verify0','restore1','verify1','controls','graph']:
   io=IO(fail);r=restore(io,self.original());self.assertFalse(r['restored']);self.assertTrue(r['errors']);self.assertFalse(r['capture_authorized'])
 def test_final_idle_is_not_replaced_by_initial_idle(self):
  io=IO();initial=io.full_idle;calls=[]
  def final():
   calls.append(1)
   if len(calls)==2:raise RuntimeError('late camera holder')
   return initial()
  io.full_idle=final;r=restore(io,self.original());self.assertFalse(r['restored'])
if __name__=='__main__':unittest.main()
