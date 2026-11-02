# SPDX-License-Identifier: GPL-3.0-or-later
from dataclasses import replace
import unittest
from attempt import Attempts, Closure, Evidence, Idle, run


class Clock:
    def __init__(self): self.now = 100.
    def __call__(self): return self.now


class Fake:
    def __init__(self, request):
        self.r = request
        self.calls = []
        self.errors = set()
        self.values = dict(
            preflight=Idle(request.boot,True,True,True,True),
            acquire=Evidence(request.nonce,request.boot,request.uid,100.,
                True,True,True,True,True,True,True,True,True),
            stop=Closure(True,True,True,True,True), restore=True,
            idle=Idle(request.boot,True,True,True,True))
    def action(self,name):
        self.calls.append(name)
        if name in self.errors: raise RuntimeError('synthetic injected failure')
        return self.values[name]
    def preflight(self,r): return self.action('preflight')
    def acquire(self,r): return self.action('acquire')
    def stop(self,r): return self.action('stop')
    def restore(self,r): return self.action('restore')
    def idle(self,r): return self.action('idle')


class Tests(unittest.TestCase):
    def fixture(self):
        clock=Clock(); attempts=Attempts('synthetic-boot',clock)
        request=attempts.issue(1000,'sddm')
        return clock,attempts,request,Fake(request)
    def execute(self, change=lambda f:None, cancelled=lambda:False):
        clock,a,r,f=self.fixture(); change(f)
        result=run(a,r,f,cancelled)
        self.assertIs(result.authentication_allowed,False)
        self.assertIs(result.password_fallback,True)
        return result,f
    def test_all_true_is_still_inactive(self):
        out,f=self.execute()
        self.assertTrue(out.evidence_eligible_for_future_validation)
        self.assertTrue(out.shutdown_confirmed)
        self.assertFalse(out.hold_required)
        self.assertEqual(f.calls,['preflight','acquire','stop','restore','idle'])
    def test_each_evidence_condition_blocks(self):
        for name in ('complete_rgb_ir','verified_timebase','quality_passed',
                     'geometry_qualified','identity_qualified','pad_qualified',
                     'single_candidate','identity_matches_account','versions_match'):
            for value in (False,None,1,'true'):
                with self.subTest(name=name,value=value):
                    out,_=self.execute(lambda f:f.values.update(acquire=replace(f.values['acquire'],**{name:value})))
                    self.assertFalse(out.evidence_eligible_for_future_validation)
                    self.assertIn(name,out.reasons)
    def test_cross_account_boot_nonce_or_time_blocks(self):
        for field,value in [('uid',1001),('uid',True),('boot','other'),('nonce','other'),
                            ('captured',99.),('captured',101.),('captured',float('nan')),
                            ('captured',float('inf')),('captured','100')]:
            with self.subTest(field=field,value=value):
                out,_=self.execute(lambda f:f.values.update(acquire=replace(f.values['acquire'],**{field:value})))
                self.assertFalse(out.evidence_eligible_for_future_validation)
                self.assertTrue(out.shutdown_confirmed)
    def test_none_evidence_blocks(self):
        out,_=self.execute(lambda f:f.values.update(acquire=None))
        self.assertIn('missing_evidence',out.reasons)
    def test_start_exception_still_stops_and_restores(self):
        out,f=self.execute(lambda f:f.errors.add('acquire'))
        self.assertTrue(out.shutdown_confirmed)
        self.assertEqual(f.calls,['preflight','acquire','stop','restore','idle'])
        self.assertFalse(out.evidence_eligible_for_future_validation)
    def test_incomplete_stop_never_restores_ioctl(self):
        for field in ('worker_stopped','light_off','native_closed','kernel_stopped','root_closed'):
            with self.subTest(field=field):
                out,f=self.execute(lambda f:f.values.update(stop=replace(f.values['stop'],**{field:False})))
                self.assertTrue(out.hold_required)
                self.assertFalse(out.shutdown_confirmed)
                self.assertNotIn('restore',f.calls)
                self.assertEqual(f.calls[-1],'idle')
    def test_stop_raises_does_not_skip_final_read(self):
        out,f=self.execute(lambda f:f.errors.add('stop'))
        self.assertTrue(out.hold_required)
        self.assertEqual(f.calls,['preflight','acquire','stop','idle'])
    def test_restore_or_idle_exception_retains_hold(self):
        for field in ('restore','idle'):
            with self.subTest(field=field):
                out,f=self.execute(lambda f:f.errors.add(field))
                self.assertTrue(out.hold_required)
                self.assertFalse(out.evidence_eligible_for_future_validation)
                self.assertEqual(f.calls[-1],'idle')
    def test_false_restore_does_not_count_truthiness(self):
        out,_=self.execute(lambda f:f.values.update(restore=1))
        self.assertTrue(out.hold_required)
    def test_busy_unknown_or_wrong_boot_preflight_never_starts(self):
        for value in (None,Idle('other',True,True,True,True),
                      Idle('synthetic-boot',True,False,True,True),
                      Idle('synthetic-boot',True,True,False,True),
                      Idle('synthetic-boot',True,True,True,False)):
            with self.subTest(value=value):
                out,f=self.execute(lambda f:f.values.update(preflight=value))
                self.assertEqual(f.calls,['preflight'])
                self.assertFalse(out.shutdown_confirmed)
    def test_final_idle_each_condition_required(self):
        for field in ('complete','camera_clients_empty','all_eight_suspended','strobe_off'):
            with self.subTest(field=field):
                out,_=self.execute(lambda f:f.values.update(idle=replace(f.values['idle'],**{field:False})))
                self.assertTrue(out.hold_required)
    def test_cancel_before_start_never_touches(self):
        out,f=self.execute(cancelled=lambda:True)
        self.assertEqual(f.calls,[])
        self.assertFalse(out.hold_required)
    def test_cancel_after_preflight_never_acquires(self):
        calls=iter([False,True])
        out,f=self.execute(cancelled=lambda:next(calls))
        self.assertEqual(f.calls,['preflight'])
    def test_cancel_after_capture_still_closes(self):
        calls=iter([False,False,True,True])
        out,f=self.execute(cancelled=lambda:next(calls))
        self.assertTrue(out.shutdown_confirmed)
        self.assertFalse(out.evidence_eligible_for_future_validation)
    def test_cancel_during_release_invalidates_completed_evidence(self):
        calls=iter([False,False,False,True])
        out,f=self.execute(cancelled=lambda:next(calls))
        self.assertTrue(out.shutdown_confirmed)
        self.assertFalse(out.evidence_eligible_for_future_validation)
        self.assertIn('expired_or_cancelled_during_release',out.reasons)
    def test_deadline_during_release_invalidates_completed_evidence(self):
        c,a,r,f=self.fixture();old=f.stop
        def stop(r):
            value=old(r);c.now=r.deadline;return value
        f.stop=stop;out=run(a,r,f)
        self.assertTrue(out.shutdown_confirmed)
        self.assertFalse(out.evidence_eligible_for_future_validation)
    def test_expiration_before_claim_never_calls_adapter(self):
        c,a,r,f=self.fixture();c.now=r.deadline
        out=run(a,r,f);self.assertEqual(f.calls,[])
        self.assertEqual(out.reasons,('claim_rejected',))
    def test_cross_account_modified_claim_burns_original(self):
        c,a,r,f=self.fixture()
        out=run(a,replace(r,uid=1001),f)
        out2=run(a,r,f)
        self.assertEqual(out.reasons,out2.reasons)
        self.assertEqual(f.calls,[])
    def test_replay_never_touches_adapter(self):
        c,a,r,f=self.fixture();run(a,r,f);f.calls.clear()
        out=run(a,r,f);self.assertEqual(f.calls,[])
        self.assertEqual(out.reasons,('claim_rejected',))
    def test_after_deadline_capture_rejected_but_closed(self):
        c,a,r,f=self.fixture()
        old=f.acquire
        def acquire(r):
            value=old(r);c.now=r.deadline;return value
        f.acquire=acquire
        out=run(a,r,f)
        self.assertTrue(out.shutdown_confirmed)
        self.assertFalse(out.evidence_eligible_for_future_validation)
    def test_invalid_issue_and_capacity(self):
        c=Clock();a=Attempts('synthetic-boot',c)
        for uid,service,ttl in [(0,'sddm',8),(True,'sddm',8),(1000,'ssh',8),
                                (1000,'kde',9),(1000,'kde',float('nan'))]:
            with self.assertRaises(ValueError):a.issue(uid,service,ttl)
        for _ in range(16):a.issue(1000,'kde')
        with self.assertRaises(ValueError):a.issue(1000,'kde')
        c.now+=9;a.issue(1000,'kde');self.assertEqual(len(a.pending),1)
    def test_production_adapter_is_not_provided(self):
        import attempt
        self.assertFalse(hasattr(attempt,'CameraAdapter'))


if __name__=='__main__':unittest.main()
