import copy
import multiprocessing
from pathlib import Path
import tempfile
import unittest

import presence as p

BOOT = 'test-boot'
PLAN = 'a'*64


def running():
    s = p.arm(p.new_session(BOOT), BOOT, PLAN)
    s = p.ready(s, BOOT, 100)
    return p.claim(s, BOOT, 101, PLAN)


def evidence(s):
    receipt = {key:s[key] for key in ('session_id','boot_id','plan_sha256')}
    receipt.update(root_session_closed=True, worker_closed_cleanly=True,
                   light_disarmed=True, kernel_closure_verified=True, cleanup_errors=[])
    idle = dict(boot_id=BOOT,checked_at=105,strobe=p.IDLE_STROBE,camera_holders=[],
                power={node:'suspended' for node in p.POWER_NODES})
    return receipt,idle


def competing_claim(folder, channel):
    try:
        p.Store(folder).update(lambda s: p.claim(s,BOOT,101,PLAN))
        channel.send('claimed')
    except p.GateError:
        channel.send('blocked')


class PresenceTests(unittest.TestCase):
    def test_preparing_cannot_confirm_or_launch(self):
        s=p.new_session(BOOT)
        with self.assertRaises(p.GateError):p.ready(s,BOOT,100)
        with self.assertRaises(p.GateError):p.claim(s,BOOT,100,PLAN)
        self.assertFalse(p.presentation(s)[3])

    def test_presence_is_bound_to_boot_and_plan(self):
        s=p.ready(p.arm(p.new_session(BOOT),BOOT,PLAN),BOOT,100)
        for boot,plan in [('different',PLAN),(BOOT,'b'*64)]:
            with self.assertRaises(p.GateError):p.claim(s,boot,101,plan)
        self.assertEqual(p.claim(s,BOOT,101,PLAN)['phase'],'running')

    def test_stale_or_backwards_time_requires_new_click(self):
        s=p.ready(p.arm(p.new_session(BOOT),BOOT,PLAN),BOOT,100)
        for now in [99,221,float('nan'),float('inf')]:
            with self.subTest(now=now),self.assertRaises(p.GateError):p.claim(s,BOOT,now,PLAN)
        self.assertEqual(p.expire(s,BOOT,221)['phase'],'awaiting_presence')

    def test_ready_can_be_consumed_only_once(self):
        s=running()
        with self.assertRaises(p.GateError):p.claim(s,BOOT,102,PLAN)
        with self.assertRaises(p.GateError):p.ready(s,BOOT,102)

    def test_cancel_before_capture_revokes_presence(self):
        s=p.ready(p.arm(p.new_session(BOOT),BOOT,PLAN),BOOT,100)
        s=p.cancel(s,BOOT)
        self.assertEqual(s['phase'],'cancelled')
        with self.assertRaises(p.GateError):p.claim(s,BOOT,101,PLAN)

    def test_cancel_during_capture_waits_for_cleanup(self):
        s=p.cancel(running(),BOOT)
        self.assertTrue(s['stop_requested']);self.assertFalse(s['safe_to_leave'])
        self.assertEqual(p.presentation(s)[0],'Stopping the trial')
        r,i=evidence(s)
        self.assertEqual(p.finish(s,BOOT,r,i,106)['phase'],'finished')

    def test_finished_requires_every_cleanup_proof(self):
        s=running();r,i=evidence(s)
        for key in ['root_session_closed','worker_closed_cleanly','light_disarmed','kernel_closure_verified','cleanup_errors']:
            broken=copy.deepcopy(r);del broken[key]
            with self.subTest(key=key),self.assertRaises(p.GateError):p.finish(s,BOOT,broken,i,106)

    def test_receipt_for_other_run_or_plan_rejected(self):
        s=running();r,i=evidence(s)
        for key in ['session_id','boot_id','plan_sha256']:
            broken=dict(r);broken[key]='other'
            with self.subTest(key=key),self.assertRaises(p.GateError):p.finish(s,BOOT,broken,i,106)

    def test_unknown_busy_or_stale_hardware_never_says_finished(self):
        s=running();r,i=evidence(s)
        cases=[{'strobe':'armed=1'}, {'camera_holders':[[123,'/dev/video0']]},
               {'power':{}},{'checked_at':100},{'checked_at':107},{'boot_id':'other'}]
        for node in p.POWER_NODES:
            cases.append({'power':{**i['power'],node:'active'}})
        for change in cases:
            with self.subTest(change=change),self.assertRaises(p.GateError):p.finish(s,BOOT,r,{**i,**change},106)

    def test_safe_failure_of_image_quality_does_not_trap_user(self):
        s=running();r,i=evidence(s);r['quality_target_met']=False
        done=p.finish(s,BOOT,r,i,106)
        self.assertEqual(p.presentation(done)[0],'Finished')
        self.assertTrue(done['safe_to_leave'])

    def test_error_does_not_claim_safe_completion(self):
        s=p.failure(running(),BOOT,'Missing cleanup')
        self.assertFalse(s['safe_to_leave']);self.assertTrue(s['stop_requested'])
        self.assertEqual(p.presentation(s)[0],'Check needed')

    def test_store_is_private_and_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as td:
            store=p.Store(Path(td)/'session');store.create(p.new_session(BOOT))
            self.assertEqual(store.path.stat().st_mode & 0o777,0o600)
            with self.assertRaises(FileExistsError):store.create(p.new_session(BOOT))
            store.folder.chmod(0o755)
            with self.assertRaises(p.GateError):store.read()

    def test_two_controllers_cannot_claim_one_click(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)/'session';store=p.Store(folder)
            store.create(p.ready(p.arm(p.new_session(BOOT),BOOT,PLAN),BOOT,100))
            ctx=multiprocessing.get_context('fork')
            channels=[ctx.Pipe(duplex=False) for _ in range(2)]
            workers=[ctx.Process(target=competing_claim,args=(folder,pair[1])) for pair in channels]
            for worker in workers:worker.start()
            for worker in workers:worker.join(5);self.assertEqual(worker.exitcode,0)
            self.assertTrue(all(pair[0].poll(2) for pair in channels))
            self.assertEqual(sorted(pair[0].recv() for pair in channels),['blocked','claimed'])
            for pair in channels:
                for end in pair:end.close()


if __name__=='__main__':unittest.main()
