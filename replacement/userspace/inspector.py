# SPDX-License-Identifier: GPL-3.0-only
# Project change2026-11-02: bounded whole-scan handling of thread inventory exhaustion.
#!/usr/bin/python3 -I
"""Fixed, bounded SP7 metadata reader. No device opens, ioctl, writes or children."""
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import resource
import re
import signal
import socket
import stat
import sys
import time

MACHINE_ID = '00000000000000000000000000000000'
HOST = 'sp7-example'
KERNEL = '7.2.11-arch1-1-surface'
INSTALLED = '/usr/local/libexec/sp7-independent/inspect'
POWER_NODES = (
    '/sys/bus/pci/devices/0000:00:05.0',
    '/sys/bus/intel-ipu4-bus/devices/intel-ipu4-mmu0',
    '/sys/bus/intel-ipu4-bus/devices/intel-ipu60',
    '/sys/bus/intel-ipu4-bus/devices/intel-ipu4-mmu1',
    '/sys/bus/intel-ipu4-bus/devices/intel-ipu4-psys0',
    '/sys/bus/i2c/devices/i2c-INT347E:00',
    '/sys/bus/i2c/devices/i2c-INT33BE:00',
    '/sys/bus/i2c/devices/i2c-INT347A:00',
)
STROBE = '/sys/bus/i2c/devices/i2c-INT347E:00/ir_strobe_test'


class Unknown(RuntimeError):
    pass


class SnapshotChanged(Unknown):
    """A complete task snapshot may be retried, never treated as empty."""
    pass


class System:
    def same_memory(self, first_tid, second_tid):
        return self._same_resource(first_tid, second_tid, 1)

    def same_files(self, first_tid, second_tid):
        return self._same_resource(first_tid, second_tid, 2)

    def _same_resource(self, first_tid, second_tid, kind):
        # Fixed read-only KCMP_VM/KCMP_FILES only; neither is a CLI option.
        if kind not in (1,2):raise Unknown('unsupported_kcmp_resource')
        if os.uname().machine!='x86_64' or ctypes.sizeof(ctypes.c_void_p)!=8:
            raise Unknown('unsupported_kcmp_architecture')
        if not hasattr(self,'_kcmp_syscall'):
            function=ctypes.CDLL(None,use_errno=True).syscall
            function.restype=ctypes.c_long;function.argtypes=[ctypes.c_long]*6
            self._kcmp_syscall=function
        result=self._kcmp_syscall(312,first_tid,second_tid,kind,0,0)
        if result not in (0,1,2,3):
            if result==-1 and ctypes.get_errno()==errno.ESRCH:
                raise SnapshotChanged('task_exited_during_kcmp:tids='+str(first_tid)+','+str(second_tid))
            raise Unknown('kcmp_errno='+str(ctypes.get_errno())+':kind='+str(kind)+':tids='+str(first_tid)+','+str(second_tid))
        return result==0

    def read(self, path):
        # All call sites select fixed metadata paths or numeric proc entries.
        try:
            with open(path, 'r') as stream:
                value = stream.read(1048577)
        except FileNotFoundError:
            raise SnapshotChanged('FileNotFoundError:read:'+path) from None
        except OSError as exc:
            # A thread can exit between opening and reading its proc stat fd.
            # Only this numeric task-identity metadata path is transient. Never
            # reclassify permission, mapping, camera, sysfs or arbitrary ESRCH.
            if exc.errno==errno.ESRCH and re.fullmatch(r'/proc/[1-9][0-9]*/task/[1-9][0-9]*/stat',path):
                raise SnapshotChanged('task_exited_during_proc_stat:'+path) from None
            raise Unknown(type(exc).__name__+':read:'+path) from None
        if len(value) > 1048576:
            raise Unknown('metadata_too_large')
        return value
    def metadata(self, operation, path, function):
        try:return function(path)
        except FileNotFoundError:
            raise SnapshotChanged('FileNotFoundError:'+operation+':'+path) from None
        except OSError as exc:
            # Only our fixed/generated metadata path, never a link target or contents.
            raise Unknown(type(exc).__name__+':'+operation+':'+path) from None
    def names(self, path): return self.metadata('list',path,os.listdir)
    def stat(self, path):
        try:return os.stat(path)
        except FileNotFoundError:
            if path.startswith('/proc/self/fd/'):raise
            raise SnapshotChanged('FileNotFoundError:stat:'+path) from None
        except OSError as exc:raise Unknown(type(exc).__name__+':stat:'+path) from None
    def link(self, path): return self.metadata('link',path,os.readlink)


def protected(path, directory=False):
    info = path.lstat()
    if (info.st_uid != 0 or info.st_mode & 0o022 or
            not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))):
        raise Unknown('unprotected_installation')


def trusted_entry():
    if len(sys.argv) != 1 or not sys.flags.isolated:
        raise Unknown('no_arguments_isolated_python_required')
    if os.geteuid() != 0 or os.environ.get('SUDO_UID') != '1000':
        raise Unknown('authorized_uid_1000_required')
    path = Path(INSTALLED)
    # sudo may execute a digest-checked script through /dev/fd/N.
    if Path(__file__).resolve(strict=True) != path:
        raise Unknown('fixed_installed_path_required')
    protected(path)
    for parent in path.parents:
        protected(parent, directory=True)
    if (socket.gethostname() != HOST or os.uname().release != KERNEL or
            Path('/etc/machine-id').read_text().strip() != MACHINE_ID):
        raise Unknown('wrong_machine_or_kernel')


def namespaces(fs):
    for kind in ('pid', 'mnt', 'user'):
        if fs.link('/proc/self/ns/'+kind) != fs.link('/proc/1/ns/'+kind):
            raise Unknown('not_host_namespace')
    mounts = [line.split() for line in fs.read('/proc/self/mountinfo').splitlines()]
    proc = [row for row in mounts if len(row) > 8 and row[4] == '/proc']
    if len(proc) != 1:
        raise Unknown('unknown_proc_mount')
    row = proc[0]; split = row.index('-')
    if row[3] != '/' or row[split+1] != 'proc':
        raise Unknown('unknown_proc_mount')
    options = (row[5]+','+row[split+3]).split(',')
    if any(x.startswith('hidepid=') and x != 'hidepid=0' for x in options):
        raise Unknown('filtered_proc_mount')


def camera_catalog(fs):
    # media devices are registered in /sys/dev/char; Linux need not expose a
    # /sys/class/media directory. Require both driver registrations and nodes.
    registered = {}; section = False
    for line in fs.read('/proc/devices').splitlines():
        if line == 'Character devices:': section = True; continue
        if line == 'Block devices:': section = False
        parts = line.split()
        if section and len(parts) == 2 and parts[1] in ('video4linux', 'media'):
            if not parts[0].isdigit() or parts[1] in registered:
                raise Unknown('invalid_camera_registration')
            registered[parts[1]] = int(parts[0])
    if registered.get('video4linux') != 81 or 'media' not in registered:
        raise Unknown('incomplete_camera_registration')
    majors=set(registered.values()); devices=set(); categories=set()
    for name in sorted(fs.names('/sys/dev/char')):
        if not re.fullmatch('[0-9]+:[0-9]+',name):
            raise Unknown('invalid_character_catalog')
        major,minor=map(int,name.split(':'))
        if major not in majors:continue
        fields=dict(line.split('=',1) for line in fs.read('/sys/dev/char/'+name+'/uevent').splitlines() if '=' in line)
        node=fields.get('DEVNAME','')
        category='video4linux' if major==81 else 'media'
        pattern='(video[0-9]+|v4l-subdev[0-9]+)' if category=='video4linux' else 'media[0-9]+'
        if (fields.get('MAJOR')!=str(major) or fields.get('MINOR')!=str(minor) or
                not re.fullmatch(pattern,node)):
            raise Unknown('unexpected_camera_node')
        devices.add((major,minor));categories.add(category)
    if categories != {'video4linux','media'}:
        raise Unknown('missing_camera_catalog')
    return devices, majors


def number_names(fs, path, maximum):
    values = sorted(int(s) for s in fs.names(path) if s.isdecimal())
    if len(values) > maximum:
        raise Unknown('inventory_limit')
    return values


def identity(fs, path):
    raw = fs.read(path+'/stat')
    # comm may contain spaces or parentheses; the fields follow its LAST ')'.
    fields = raw[raw.rfind(')')+2:].split()
    if len(fields) < 20 or not fields[19].isdigit():
        raise Unknown('invalid_task_identity')
    return int(fields[19])  # proc stat field 22: starttime


def mapping_directory(tid):
    # /proc/PID/task/TID has no map_files; /proc/TID does, including nonleaders.
    return '/proc/'+str(tid)+'/map_files'


def scan_task(fs, pid, tid, majors, tick, budget, memory_reference=None, files_reference=None):
    path='/proc/'+str(pid)+'/task/'+str(tid)
    start=identity(fs,path)
    def verify_shared_memory():
        if memory_reference is None:return
        ref_tid,ref_start=memory_reference
        ref_path='/proc/'+str(pid)+'/task/'+str(ref_tid)
        if identity(fs,ref_path)!=ref_start or not fs.same_memory(ref_tid,tid):
            raise Unknown('memory_sharing_changed:pid='+str(pid)+':tid='+str(tid))
    verify_shared_memory()
    def verify_shared_files():
        if files_reference is None:return
        ref_tid,ref_start=files_reference
        ref_path='/proc/'+str(pid)+'/task/'+str(ref_tid)
        if identity(fs,ref_path)!=ref_start or not fs.same_files(ref_tid,tid):
            raise Unknown('files_sharing_changed:pid='+str(pid)+':tid='+str(tid))
    verify_shared_files()
    for attempt in range(3):
        holders=[]
        try:
            fds=number_names(fs,path+'/fd',65536) if files_reference is None else []
            for fd in fds:
                tick();budget['inspected']+=1
                if budget['inspected']>500000:raise Unknown('metadata_limit')
                value=fs.stat(path+'/fd/'+str(fd))
                if stat.S_ISCHR(value.st_mode) and os.major(value.st_rdev) in majors:
                    budget['camera_seen']=True
                    holders.append([pid,tid,fd,os.major(value.st_rdev),os.minor(value.st_rdev)])
                    if len(holders)>1024:raise Unknown('holder_limit')
            if files_reference is None and number_names(fs,path+'/fd',65536)!=fds:
                raise SnapshotChanged('descriptor_inventory_changed')
            if memory_reference is None:
                mapping_path=mapping_directory(tid)
                mappings=sorted(fs.names(mapping_path))
                if len(mappings)>65536:raise Unknown('mapping_limit')
                for name in mappings:
                    tick();budget['inspected']+=1
                    if budget['inspected']>500000:raise Unknown('metadata_limit:pid='+str(pid)+':tid='+str(tid))
                    if not re.fullmatch('[0-9a-f]+-[0-9a-f]+',name):raise Unknown('invalid_mapping_name:pid='+str(pid)+':tid='+str(tid))
                    value=fs.stat(mapping_path+'/'+name)
                    if stat.S_ISCHR(value.st_mode) and os.major(value.st_rdev) in majors:
                        raise Unknown('camera_mapping_present:pid='+str(pid)+':tid='+str(tid))
                if sorted(fs.names(mapping_path))!=mappings:
                    raise SnapshotChanged('mapping_inventory_changed')
        except (SnapshotChanged,FileNotFoundError) as exc:
            # Never forget a camera observed in a discarded attempt. Identity,
            # permissions, deadlines and mapping-camera failures are not retried.
            if holders:raise Unknown('camera_seen_during_unstable_inventory:pid='+str(pid)+':tid='+str(tid))
            if identity(fs,path)!=start:raise Unknown('task_reused:pid='+str(pid)+':tid='+str(tid))
            if attempt==2:
                raise SnapshotChanged('thread_inventory_unstable_after_3_attempts:pid='+str(pid)+':tid='+str(tid)+':'+str(exc)) from None
            budget['rechecks']+=1
            tick()
            continue
        if identity(fs,path)!=start:raise Unknown('task_reused:pid='+str(pid)+':tid='+str(tid))
        verify_shared_memory()
        verify_shared_files()
        return (pid,tid,start),holders
    raise Unknown('incomplete_task_snapshot')


def scan(fs, majors, own_pid, tick, budget):
    pids = number_names(fs, '/proc', 8192)
    if 1 not in pids or own_pid not in pids:
        raise Unknown('incomplete_process_inventory')
    tasks = []; holders = []
    for pid in pids:
        tick()
        if pid == own_pid:
            # main closed inherited FDs >=3 before scanning; only these remain.
            for fd in (0,1,2):
                try: value = fs.stat('/proc/self/fd/'+str(fd))
                except FileNotFoundError: continue
                if stat.S_ISCHR(value.st_mode) and os.major(value.st_rdev) in majors:
                    budget['camera_seen']=True
                    holders.append([pid,pid,fd,os.major(value.st_rdev),os.minor(value.st_rdev)])
            continue
        prefix = '/proc/'+str(pid)+'/task'
        tids = number_names(fs, prefix, 32768)
        if not tids:
            raise Unknown('empty_task_inventory:pid='+str(pid))
        memory_representatives=[]
        files_representatives=[]
        for tid in tids:
            tick()
            reference=None
            for representative in memory_representatives:
                tick()
                if fs.same_memory(representative[0],tid):
                    reference=representative;break
            files_reference=None
            for representative in files_representatives:
                tick()
                if fs.same_files(representative[0],tid):
                    files_reference=representative;break
            task,found=scan_task(fs,pid,tid,majors,tick,budget,reference,files_reference)
            if reference is None:memory_representatives.append((tid,task[2]))
            if files_reference is None:files_representatives.append((tid,task[2]))
            tasks.append(task);holders.extend(found)
            if len(holders)>1024:raise Unknown('holder_limit')
        if number_names(fs, prefix, 32768) != tids:
            raise SnapshotChanged('task_inventory_changed:pid='+str(pid))
    final_pids=number_names(fs, '/proc', 8192)
    if final_pids != pids:
        added=','.join(map(str,sorted(set(final_pids)-set(pids))[:8]))
        removed=','.join(map(str,sorted(set(pids)-set(final_pids))[:8]))
        raise SnapshotChanged('process_inventory_changed:added='+added+':removed='+removed)
    return tasks, sorted(holders), budget['inspected'], budget['rechecks']


def collect(fs, own_pid, clock=time.monotonic):
    started = clock()
    def tick():
        if not 0 <= clock()-started < 4:
            raise Unknown('deadline')
    namespaces(fs)
    boot = fs.read('/proc/sys/kernel/random/boot_id').strip()
    if len(boot) != 36:
        raise Unknown('invalid_boot_id')
    catalog, majors = camera_catalog(fs)
    # At most one complete restart. All spent work shares the original deadline
    # and one metadata budget; an observed camera is never erased by a restart.
    budget={'inspected':0,'rechecks':0,'camera_seen':False}
    passes_started=0
    for attempt in range(2):
        try:
            passes_started+=1
            first, holders1, _, _ = scan(fs, majors, own_pid, tick, budget)
            passes_started+=1
            second, holders2, _, _ = scan(fs, majors, own_pid, tick, budget)
            if holders1 != holders2:
                raise Unknown('unstable_camera_snapshot')
            if first != second:
                first_ids={(pid,tid):start for pid,tid,start in first}
                second_ids={(pid,tid):start for pid,tid,start in second}
                if any(first_ids[key]!=second_ids[key] for key in first_ids.keys() & second_ids.keys()):
                    raise Unknown('task_reused_between_passes')
                raise SnapshotChanged('task_inventory_changed_between_passes')
            break
        except SnapshotChanged as exc:
            if budget['camera_seen']:
                raise Unknown('camera_seen_during_unstable_process_inventory') from None
            if attempt==1:
                raise Unknown('unstable_process_inventory_after_2_attempts:'+str(exc)) from None
            tick()
    power = {node:fs.read(node+'/power/runtime_status').strip() for node in POWER_NODES}
    strobe = fs.read(STROBE).strip()
    if camera_catalog(fs) != (catalog, majors) or fs.read('/proc/sys/kernel/random/boot_id').strip() != boot:
        raise Unknown('machine_state_changed')
    namespaces(fs)
    tick()
    return {'schema':1,'source':'sp7-ir-idle-v1','complete':True,'boot_id':boot,
            'checked_at':started,'completed_at':clock(),'camera_holders':holders2,
            'power':power,'strobe':strobe,'tasks_checked':len(second),
            'metadata_entries_checked':budget['inspected'],'passes':2,'task_rechecks':budget['rechecks'],
            'whole_scan_rechecks':attempt,'passes_started':passes_started,
            'device_catalog_sha256':hashlib.sha256(json.dumps(sorted(catalog)).encode()).hexdigest()}


def main():
    try:
        trusted_entry()
        # Enumerate once before opening metadata; cover inherited descriptors even
        # when the caller lowered RLIMIT_NOFILE after opening a high descriptor.
        for name in os.listdir('/proc/self/fd'):
            if name.isdecimal() and int(name)>=3:
                try:os.close(int(name))
                except OSError as exc:
                    if exc.errno!=9:raise
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        resource.setrlimit(resource.RLIMIT_CPU,(4,4))
        resource.setrlimit(resource.RLIMIT_AS,(128*1024*1024,128*1024*1024))
        signal.signal(signal.SIGALRM,lambda *args: (_ for _ in ()).throw(Unknown('deadline')))
        signal.alarm(4)
        result = collect(System(), os.getpid())
        signal.alarm(0)
        print(json.dumps(result, separators=(',',':')))
        return 0
    except Exception as exc:
        # Do not expose process contents, arbitrary target paths or environment.
        reason = str(exc) if isinstance(exc,Unknown) else type(exc).__name__
        print(json.dumps({'schema':1,'source':'sp7-ir-idle-v1','complete':False,'reason':reason}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
