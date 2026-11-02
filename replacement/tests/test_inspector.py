import copy
import os
from pathlib import Path
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import inspector as s

BOOT='11111111-2222-4333-8444-555555555555'

class FakeSystem:
    def __init__(self):
        self.directories={'/proc':['1','10','99'],'/proc/1/task':['1'],'/proc/10/task':['10','11'],
                          '/proc/1/task/1/fd':[],'/proc/10/task/10/fd':['0'],
                          '/proc/10/task/11/fd':['7'],'/sys/class/video4linux':['video0','v4l-subdev0'],
                          '/sys/class/media':['media0'],'/sys/dev/char':['81:0','81:1','240:0','1:3']}
        self.text={'/proc/self/mountinfo':'1 0 0:1 / /proc rw - proc proc rw\n',
                   '/proc/sys/kernel/random/boot_id':BOOT,
                   '/sys/class/video4linux/video0/dev':'81:0','/sys/class/video4linux/v4l-subdev0/dev':'81:1',
                   '/sys/class/media/media0/dev':'240:0',
                   '/proc/devices':'Character devices:\n 81 video4linux\n240 media\nBlock devices:\n',
                   '/sys/dev/char/81:0/uevent':'MAJOR=81\nMINOR=0\nDEVNAME=video0\n',
                   '/sys/dev/char/81:1/uevent':'MAJOR=81\nMINOR=1\nDEVNAME=v4l-subdev0\n',
                   '/sys/dev/char/240:0/uevent':'MAJOR=240\nMINOR=0\nDEVNAME=media0\n',
                   s.STROBE:'armed=0 remaining_ms=0 cleanup_pending=0 recovery_required=0'}
        self.text.update({p+'/power/runtime_status':'suspended' for p in s.POWER_NODES})
        for pid,tid in ((1,1),(10,10),(10,11)):
            self.text[f'/proc/{pid}/task/{tid}/stat']=f'{tid} (name (with) parentheses) S '+' '.join(['0']*18+['1234']+['0']*5)
            self.directories[f'/proc/{tid}/map_files']=[]
        self.metadata={'/proc/10/task/10/fd/0':self.regular(),'/proc/10/task/11/fd/7':self.regular()}
        self.deny=None;self.mutation=None;self.calls=0
    def same_memory(self,first,second):return False
    def same_files(self,first,second):return False
    def regular(self):return SimpleNamespace(st_mode=stat.S_IFREG|0o600,st_rdev=0)
    def camera(self,major=81,minor=0):return SimpleNamespace(st_mode=stat.S_IFCHR|0o600,st_rdev=os.makedev(major,minor))
    def read(self,path):return self.text[path]
    def names(self,path):return list(self.directories[path])
    def link(self,path):return 'ns:'+path.rsplit('/',1)[-1]
    def stat(self,path):
        self.calls+=1
        if self.mutation:self.mutation(path)
        if path==self.deny:raise PermissionError('denied')
        if path.startswith('/proc/self/fd/'):raise FileNotFoundError()
        return self.metadata[path]

class ScannerTests(unittest.TestCase):
    def setUp(self):self.fs=FakeSystem()
    def collect(self):return s.collect(self.fs,99,lambda:100.)
    def test_idle_snapshot_covers_threads_and_eight_devices(self):
        r=self.collect();self.assertTrue(r['complete']);self.assertEqual(r['camera_holders'],[])
        self.assertEqual(r['tasks_checked'],3);self.assertEqual(r['passes'],2)
        self.assertEqual(r['metadata_entries_checked'],4);self.assertEqual(len(r['power']),8)
    def test_worker_thread_camera_is_found_by_device_number(self):
        self.fs.metadata['/proc/10/task/11/fd/7']=self.fs.camera(81,77)
        self.assertEqual(self.collect()['camera_holders'],[[10,11,7,81,77]])
    def test_media_descriptor_detected_even_with_nonstandard_target_name(self):
        self.fs.metadata['/proc/10/task/11/fd/7']=self.fs.camera(240,3)
        self.assertEqual(self.collect()['camera_holders'][0][-2:],[240,3])
    def test_non_camera_character_device_is_not_misclassified(self):
        self.fs.metadata['/proc/10/task/11/fd/7']=self.fs.camera(1,3)
        self.assertEqual(self.collect()['camera_holders'],[])
    def test_permission_denied_never_returns_complete(self):
        self.fs.deny='/proc/10/task/11/fd/7'
        with self.assertRaises(PermissionError):self.collect()
    def test_disappearing_descriptor_is_unknown(self):
        def gone(path):
            if path=='/proc/10/task/11/fd/7':raise FileNotFoundError()
        self.fs.mutation=gone
        with self.assertRaisesRegex(s.Unknown,'unstable_after_3_attempts'):self.collect()
    def test_empty_thread_inventory_is_unknown(self):
        self.fs.directories['/proc/10/task']=[]
        with self.assertRaises(s.Unknown):self.collect()
    def test_new_unreadable_process_is_not_skipped(self):
        self.fs.mutation=lambda path:self.fs.directories['/proc'].append('55') if '55' not in self.fs.directories['/proc'] else None
        original=self.fs.names
        def names(path):
            if path=='/proc/55/task':raise PermissionError('new process unreadable')
            return original(path)
        self.fs.names=names
        with self.assertRaises(PermissionError):self.collect()

    def add_process(self, camera=False):
        self.fs.directories['/proc'].append('55')
        self.fs.directories['/proc/55/task']=['55']
        self.fs.directories['/proc/55/task/55/fd']=['3']
        self.fs.directories['/proc/55/map_files']=[]
        self.fs.text['/proc/55/task/55/stat']=self.fs.text['/proc/1/task/1/stat']
        self.fs.metadata['/proc/55/task/55/fd/3']=self.fs.camera() if camera else self.fs.regular()

    def test_new_process_requires_two_new_complete_passes(self):
        def change(path):
            self.add_process();self.fs.mutation=None
        self.fs.mutation=change
        value=self.collect()
        self.assertTrue(value['complete']);self.assertEqual(value['tasks_checked'],4)
        self.assertEqual(value['whole_scan_rechecks'],1)
        self.assertEqual(value['passes_started'],3)
        self.assertEqual(value['metadata_entries_checked'],8)

    def test_camera_in_new_process_is_found_after_restart(self):
        def change(path):
            self.add_process(camera=True);self.fs.mutation=None
        self.fs.mutation=change
        self.assertEqual(self.collect()['camera_holders'],[[55,55,3,81,0]])

    def test_exited_process_is_followed_by_two_complete_passes(self):
        def change(path):
            self.fs.directories['/proc'].remove('10');self.fs.mutation=None
        self.fs.mutation=change
        value=self.collect()
        self.assertTrue(value['complete']);self.assertEqual(value['tasks_checked'],1)
        self.assertEqual(value['whole_scan_rechecks'],1)

    def test_camera_in_exited_process_is_not_forgotten(self):
        self.fs.metadata['/proc/10/task/11/fd/7']=self.fs.camera()
        def change(path):
            self.fs.directories['/proc'].remove('10');self.fs.mutation=None
        self.fs.mutation=change
        with self.assertRaisesRegex(s.Unknown,'camera_seen_during_unstable_process'):self.collect()

    def test_process_exits_before_its_task_list_can_be_read(self):
        original=self.fs.names
        def names(path):
            if path=='/proc/10/task':
                self.fs.directories['/proc'].remove('10')
                raise s.SnapshotChanged('FileNotFoundError:list:'+path)
            return original(path)
        self.fs.names=names
        value=self.collect()
        self.assertEqual(value['whole_scan_rechecks'],1)
        self.assertEqual(value['tasks_checked'],1)

    def test_repeated_whole_inventory_change_is_bounded(self):
        self.add_process();self.fs.directories['/proc'].remove('55')
        original=self.fs.names;calls=0
        def names(path):
            nonlocal calls
            if path=='/proc':
                calls+=1
                if calls in (2,4):
                    if '55' in self.fs.directories[path]:self.fs.directories[path].remove('55')
                    else:self.fs.directories[path].append('55')
            return original(path)
        self.fs.names=names
        with self.assertRaisesRegex(s.Unknown,'after_2_attempts'):self.collect()
        self.assertEqual(calls,4)

    def test_restart_does_not_reset_metadata_budget(self):
        def change(path):
            self.add_process();self.fs.mutation=None
        self.fs.mutation=change
        original=s.scan;calls=0
        def scan(fs,majors,pid,tick,budget):
            nonlocal calls
            calls+=1
            if calls==1:budget['inspected']=499997
            return original(fs,majors,pid,tick,budget)
        with patch.object(s,'scan',side_effect=scan),self.assertRaisesRegex(s.Unknown,'metadata_limit'):
            self.collect()
        self.assertEqual(calls,2)

    def test_restart_does_not_reset_deadline(self):
        now=100.
        def change(path):
            nonlocal now
            self.add_process();self.fs.mutation=None;now=105.
        self.fs.mutation=change
        with self.assertRaisesRegex(s.Unknown,'deadline'):s.collect(self.fs,99,lambda:now)

    def test_identity_reuse_between_whole_passes_blocks(self):
        original=self.fs.names;calls=0
        def names(path):
            nonlocal calls
            if path=='/proc':
                calls+=1
                if calls==3:self.fs.text['/proc/10/task/11/stat']=self.fs.text['/proc/10/task/11/stat'].replace('1234','5678')
            return original(path)
        self.fs.names=names
        with self.assertRaisesRegex(s.Unknown,'task_reused_between_passes'):self.collect()

    def test_camera_seen_in_first_pass_blocks_second_pass_discard(self):
        self.fs.metadata['/proc/10/task/11/fd/7']=self.fs.camera()
        original=self.fs.names;calls=0
        def names(path):
            nonlocal calls
            if path=='/proc':
                calls+=1
                if calls==4:self.add_process()
            return original(path)
        self.fs.names=names
        with self.assertRaisesRegex(s.Unknown,'camera_seen_during_unstable_process'):self.collect()
    def test_reused_thread_is_unknown(self):
        self.fs.mutation=lambda path:self.fs.text.update({'/proc/10/task/11/stat':self.fs.text['/proc/10/task/11/stat'].replace('1234','5678')}) if path=='/proc/10/task/11/fd/7' else None
        with self.assertRaises(s.Unknown):self.collect()
    def test_second_pass_holder_difference_is_unknown(self):
        count=0
        def change(path):
            nonlocal count
            if path.endswith('/11/fd/7'):
                count+=1
                if count==2:self.fs.metadata[path]=self.fs.camera()
        self.fs.mutation=change
        with self.assertRaises(s.Unknown):self.collect()
    def test_missing_device_catalog_is_unknown(self):
        self.fs.directories['/sys/dev/char'].remove('240:0')
        with self.assertRaises(s.Unknown):self.collect()
    def test_memory_mapped_camera_without_open_fd_blocks(self):
        self.fs.directories['/proc/11/map_files']=['abcd-ffff']
        self.fs.metadata['/proc/11/map_files/abcd-ffff']=self.fs.camera()
        with self.assertRaisesRegex(s.Unknown,'camera_mapping'):self.collect()
    def test_unreadable_mapping_blocks(self):
        self.fs.directories['/proc/11/map_files']=['abcd-ffff']
        self.fs.deny='/proc/11/map_files/abcd-ffff'
        with self.assertRaises(PermissionError):self.collect()
    def test_real_linux_thread_mapping_directory(self):
        import threading
        observed=[]
        def inspect_thread():
            tid=threading.get_native_id()
            observed.append(Path(s.mapping_directory(tid)).is_dir())
            observed.append((Path('/proc')/str(os.getpid())/'task'/str(tid)/'map_files').exists())
        t=threading.Thread(target=inspect_thread);t.start();t.join()
        self.assertEqual(observed,[True,False])
    def test_metadata_error_reports_only_selected_path(self):
        with patch.object(s.os,'listdir',side_effect=PermissionError('secret details')):
            with self.assertRaisesRegex(s.Unknown,'PermissionError:list:/proc/123/map_files') as exc:
                s.System().names('/proc/123/map_files')
        self.assertNotIn('secret',str(exc.exception))
    def test_closed_own_standard_descriptor_remains_file_not_found(self):
        with patch.object(s.os,'stat',side_effect=FileNotFoundError()):
            with self.assertRaises(FileNotFoundError):s.System().stat('/proc/self/fd/0')
    def test_missing_init_process_blocks(self):
        self.fs.directories['/proc'].remove('1')
        with self.assertRaises(s.Unknown):self.collect()
    def test_fd_added_during_scan_blocks(self):
        self.fs.metadata['/proc/10/task/11/fd/8']=self.fs.regular()
        self.fs.mutation=lambda path:self.fs.directories['/proc/10/task/11/fd'].append('8') if path.endswith('/11/fd/7') else None
        with self.assertRaises(s.Unknown):self.collect()
    def test_media_class_directory_is_not_required(self):
        del self.fs.directories['/sys/class/media']
        self.assertTrue(self.collect()['complete'])
    def test_inconsistent_uevent_blocks(self):
        self.fs.text['/sys/dev/char/240:0/uevent']='MAJOR=241\nMINOR=0\nDEVNAME=media0\n'
        with self.assertRaises(s.Unknown):self.collect()
    def test_missing_media_registration_blocks(self):
        self.fs.text['/proc/devices']='Character devices:\n81 video4linux\n'
        with self.assertRaises(s.Unknown):self.collect()
    def test_wrong_namespace_is_unknown(self):
        self.fs.link=lambda path:path
        with self.assertRaises(s.Unknown):self.collect()
    def test_transient_disappearing_fd_gets_full_retry(self):
        def change(path):
            if path.endswith('/11/fd/7'):
                self.fs.directories['/proc/10/task/11/fd']=[]
                self.fs.mutation=None
                raise FileNotFoundError()
        self.fs.mutation=change
        value=self.collect()
        self.assertTrue(value['complete']);self.assertEqual(value['task_rechecks'],1)
    def test_added_camera_cannot_be_lost_in_retry(self):
        def change(path):
            if path.endswith('/11/fd/7'):
                self.fs.directories['/proc/10/task/11/fd'].append('8')
                self.fs.metadata['/proc/10/task/11/fd/8']=self.fs.camera()
                self.fs.mutation=None
        self.fs.mutation=change
        self.assertEqual(self.collect()['camera_holders'],[[10,11,8,81,0]])
    def test_camera_seen_in_discarded_attempt_still_blocks(self):
        self.fs.metadata['/proc/10/task/11/fd/7']=self.fs.camera()
        self.fs.mutation=lambda path:self.fs.directories['/proc/10/task/11/fd'].clear() if path.endswith('/11/fd/7') else None
        with self.assertRaisesRegex(s.Unknown,'camera_seen_during_unstable'):self.collect()
    def test_transient_mapping_change_gets_full_retry(self):
        self.fs.directories['/proc/11/map_files']=['a-b']
        self.fs.metadata['/proc/11/map_files/a-b']=self.fs.regular()
        def change(path):
            if path=='/proc/11/map_files/a-b':
                self.fs.directories['/proc/11/map_files']=[];self.fs.mutation=None
                raise FileNotFoundError()
        self.fs.mutation=change
        self.assertEqual(self.collect()['task_rechecks'],1)
    def test_permanent_mapping_churn_is_bounded_and_identifies_thread(self):
        def unstable(path):
            if path.endswith('/11/fd/7'):
                self.fs.directories['/proc/11/map_files']=['a-b']
            if path=='/proc/11/map_files/a-b':self.fs.directories['/proc/11/map_files']=[]
        self.fs.metadata['/proc/11/map_files/a-b']=self.fs.regular();self.fs.mutation=unstable
        with self.assertRaisesRegex(s.Unknown,'unstable_after_3_attempts:pid=10:tid=11'):self.collect()
    def test_permission_denied_is_never_retried(self):
        self.fs.deny='/proc/10/task/11/fd/7'
        with self.assertRaises(PermissionError):self.collect()
        self.assertEqual(self.fs.calls,2)
    def test_camera_mapping_observation_is_never_retried(self):
        self.fs.directories['/proc/11/map_files']=['a-b']
        self.fs.metadata['/proc/11/map_files/a-b']=self.fs.camera()
        def change(path):
            if path=='/proc/11/map_files/a-b':self.fs.directories['/proc/11/map_files']=[]
        self.fs.mutation=change
        with self.assertRaisesRegex(s.Unknown,'camera_mapping_present:pid=10:tid=11'):self.collect()
    def test_shared_memory_scanned_once_but_every_fd_table_scanned(self):
        self.fs.same_memory=lambda first,second:True
        self.fs.directories['/proc/10/map_files']=['a-b']
        self.fs.metadata['/proc/10/map_files/a-b']=self.fs.regular()
        del self.fs.directories['/proc/11/map_files']
        self.fs.metadata['/proc/10/task/11/fd/7']=self.fs.camera()
        value=self.collect()
        self.assertEqual(value['camera_holders'],[[10,11,7,81,0]])
        self.assertEqual(value['metadata_entries_checked'],6)
    def test_private_memory_camera_is_not_skipped(self):
        self.fs.directories['/proc/11/map_files']=['a-b']
        self.fs.metadata['/proc/11/map_files/a-b']=self.fs.camera()
        with self.assertRaisesRegex(s.Unknown,'camera_mapping_present'):self.collect()
    def test_unknown_sharing_blocks(self):
        self.fs.same_memory=lambda *args:(_ for _ in ()).throw(s.Unknown('kcmp_denied'))
        with self.assertRaisesRegex(s.Unknown,'kcmp_denied'):self.collect()
    def test_kcmp_exited_task_is_recheckable_but_permission_denied_is_not(self):
        system=s.System();system._kcmp_syscall=lambda *args:-1
        with patch.object(s.os,'uname',return_value=SimpleNamespace(machine='x86_64')):
            with patch.object(s.ctypes,'get_errno',return_value=s.errno.ESRCH):
                with self.assertRaises(s.SnapshotChanged):system.same_memory(10,11)
            with patch.object(s.ctypes,'get_errno',return_value=s.errno.EPERM):
                with self.assertRaises(s.Unknown) as error:system.same_memory(10,11)
                self.assertNotIsInstance(error.exception,s.SnapshotChanged)
    def test_sharing_change_before_fd_scan_blocks(self):
        answers=iter([True,False])
        self.fs.same_memory=lambda *args:next(answers)
        with self.assertRaisesRegex(s.Unknown,'memory_sharing_changed'):self.collect()
    def test_sharing_change_after_fd_scan_blocks(self):
        answers=iter([True,True,False])
        self.fs.same_memory=lambda *args:next(answers)
        with self.assertRaisesRegex(s.Unknown,'memory_sharing_changed'):self.collect()
    def test_shared_memory_reference_identity_change_blocks(self):
        def compare(*args):
            self.fs.text['/proc/10/task/10/stat']=self.fs.text['/proc/10/task/10/stat'].replace('1234','5678')
            return True
        self.fs.same_memory=compare
        with self.assertRaisesRegex(s.Unknown,'memory_sharing_changed'):self.collect()
    def test_large_shared_map_set_does_not_repeat_metadata_for_threads(self):
        self.fs.same_memory=lambda *args:True
        self.fs.directories['/proc/10/task']=[str(tid) for tid in range(10,210)]
        self.fs.directories['/proc/10/map_files']=[format(i,'x')+'-'+format(i+1,'x') for i in range(3000)]
        for name in self.fs.directories['/proc/10/map_files']:
            self.fs.metadata['/proc/10/map_files/'+name]=self.fs.regular()
        for tid in range(12,210):
            self.fs.text[f'/proc/10/task/{tid}/stat']=self.fs.text['/proc/10/task/11/stat']
            self.fs.directories[f'/proc/10/task/{tid}/fd']=[]
        value=self.collect()
        self.assertEqual(value['tasks_checked'],201)
        self.assertEqual(value['metadata_entries_checked'],6004)
    def shared_files(self):
        self.fs.same_files=lambda *args:True
        self.fs.directories['/proc/10/task/11/fd']=['0']
        self.fs.metadata['/proc/10/task/11/fd/0']=self.fs.metadata['/proc/10/task/10/fd/0']

    def test_shared_files_scanned_once_with_kernel_proof(self):
        self.shared_files()
        del self.fs.directories['/proc/10/task/11/fd']
        value=self.collect()
        self.assertEqual(value['metadata_entries_checked'],2)
        self.assertEqual(value['tasks_checked'],3)

    def test_shared_camera_is_still_found(self):
        self.shared_files()
        self.fs.metadata['/proc/10/task/10/fd/0']=self.fs.camera()
        self.assertEqual(self.collect()['camera_holders'],[[10,10,0,81,0]])

    def test_shared_files_do_not_skip_private_camera_mapping(self):
        self.shared_files()
        self.fs.directories['/proc/11/map_files']=['a-b']
        self.fs.metadata['/proc/11/map_files/a-b']=self.fs.camera()
        with self.assertRaisesRegex(s.Unknown,'camera_mapping_present'):self.collect()

    def test_unknown_files_sharing_blocks(self):
        self.fs.same_files=lambda *args:(_ for _ in ()).throw(s.Unknown('files_compare_denied'))
        with self.assertRaisesRegex(s.Unknown,'files_compare_denied'):self.collect()

    def test_files_sharing_change_before_scan_blocks(self):
        answers=iter([True,False]);self.fs.same_files=lambda *args:next(answers)
        with self.assertRaisesRegex(s.Unknown,'files_sharing_changed'):self.collect()

    def test_files_sharing_change_after_scan_blocks(self):
        answers=iter([True,True,False]);self.fs.same_files=lambda *args:next(answers)
        with self.assertRaisesRegex(s.Unknown,'files_sharing_changed'):self.collect()

    def test_files_reference_reused_identity_blocks(self):
        def compare(*args):
            self.fs.text['/proc/10/task/10/stat']=self.fs.text['/proc/10/task/10/stat'].replace('1234','5678')
            return True
        self.fs.same_files=compare
        with self.assertRaisesRegex(s.Unknown,'files_sharing_changed'):self.collect()

    def test_kcmp_files_uses_only_fixed_files_selector(self):
        from unittest.mock import Mock
        system=s.System();system._kcmp_syscall=Mock(return_value=0)
        with patch.object(s.os,'uname',return_value=SimpleNamespace(machine='x86_64')):
            self.assertTrue(system.same_files(10,11))
        system._kcmp_syscall.assert_called_once_with(312,10,11,2,0,0)
        with self.assertRaisesRegex(s.Unknown,'unsupported_kcmp_resource'):
            system._same_resource(10,11,99)

    def test_shared_camera_cannot_be_discarded_by_process_restart(self):
        self.shared_files();self.fs.metadata['/proc/10/task/10/fd/0']=self.fs.camera()
        def change(path):
            self.add_process();self.fs.mutation=None
        self.fs.mutation=change
        with self.assertRaisesRegex(s.Unknown,'camera_seen_during_unstable_process'):self.collect()

    def test_hidden_process_mount_rejected(self):
        self.fs.text['/proc/self/mountinfo']='1 0 0:1 / /proc rw,hidepid=2 - proc proc rw\n'
        with self.assertRaises(s.Unknown):self.collect()
    def test_missing_power_status_is_unknown(self):
        del self.fs.text[s.POWER_NODES[-1]+'/power/runtime_status']
        with self.assertRaises(KeyError):self.collect()
    def test_busy_power_is_reported_without_claiming_idle(self):
        self.fs.text[s.POWER_NODES[0]+'/power/runtime_status']='active'
        self.assertEqual(self.collect()['power'][s.POWER_NODES[0]],'active')
    def test_deadline_is_bounded(self):
        ticks=iter([100.,105.])
        with self.assertRaises(s.Unknown):s.collect(self.fs,99,lambda:next(ticks))
    def test_standard_descriptor_camera_is_not_hidden_by_self_exclusion(self):
        old=self.fs.stat
        self.fs.stat=lambda path:self.fs.camera() if path=='/proc/self/fd/0' else old(path)
        self.assertEqual(self.collect()['camera_holders'],[[99,99,0,81,0]])
    def test_no_external_argument_or_nonroot_caller(self):
        with patch.object(s.sys,'argv',['inspect','/etc/shadow']):
            with self.assertRaises(s.Unknown):s.trusted_entry()
        with patch.object(s.sys,'argv',['inspect']),patch.object(s.sys,'flags',SimpleNamespace(isolated=1)),patch.object(s.os,'geteuid',return_value=1000):
            with self.assertRaises(s.Unknown):s.trusted_entry()
    def test_unprotected_or_symlink_installation_rejected(self):
        for mode,uid in ((stat.S_IFLNK|0o777,0),(stat.S_IFREG|0o666,0),(stat.S_IFREG|0o755,1000)):
            with self.subTest(mode=mode,uid=uid),patch.object(Path,'lstat',return_value=SimpleNamespace(st_mode=mode,st_uid=uid)):
                with self.assertRaises(s.Unknown):s.protected(Path('/not-accessed'))

if __name__=='__main__':unittest.main()
