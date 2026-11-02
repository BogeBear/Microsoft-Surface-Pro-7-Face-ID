# SPDX-License-Identifier: GPL-3.0-only
"""Atomic, additive RAM staging primitive. Does not load modules or add rights.
The reviewed caller binds the destination, boot and checkpoint. No CLI.
"""
from pathlib import Path
import ctypes
import hashlib
import json
import os
import re
import stat

def ram_filesystem(path):
    lib=ctypes.CDLL(None,use_errno=True)
    lib.statfs.argtypes=[ctypes.c_char_p,ctypes.c_void_p]
    lib.statfs.restype=ctypes.c_int
    buf=ctypes.create_string_buffer(256)
    if lib.statfs(os.fsencode(path),buf):raise OSError(ctypes.get_errno(),'statfs failed')
    kind=ctypes.c_long.from_buffer(buf).value & 0xffffffff
    return kind in (0x01021994,0x858458f6)  # Linux tmpfs or ramfs

EXECUTABLES={'helper','inspect'}
NAMES={'helper','inspect','ov7251.ko','intel-ipu4p.ko','intel-ipu4p-isys.ko',
       'intel-ipu4p-psys.ko','intel-ipu4p-isys-csslib.ko','intel-ipu4p-psys-csslib.ko'}


def stage(files, destination, *, boot_path, expected_boot, checkpoint, expected_checkpoint, purpose='inactive', restoration_session=None):
    if purpose not in ('inactive','restoration_material'):raise ValueError('Unsupported staging purpose')
    destination=Path(destination)
    if os.geteuid()!=0:
        raise PermissionError('Root staging requires real system authorization')
    if not EXECUTABLES<=NAMES or any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',n) for n in NAMES):
        raise ValueError('Invalid reviewed payload policy')
    if set(files)!=NAMES or any(type(v) is not bytes or not 0<len(v)<=16*1024*1024 for v in files.values()):
        raise ValueError('Unexpected payload inventory')
    if sum(map(len,files.values()))>32*1024*1024:
        raise ValueError('Payload budget exceeded')
    for parent in [destination.parent,*destination.parent.parents]:
        s=parent.lstat()
        if not stat.S_ISDIR(s.st_mode) or s.st_uid!=0 or s.st_mode&0o022:
            raise ValueError(f'Unprotected staging ancestor: {parent}, uid={s.st_uid}, mode={s.st_mode & 0o777:o}')
    if not ram_filesystem(destination.parent):
        raise ValueError('RAM-only staging requires tmpfs or ramfs')
    def metadata(path,limit):
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):raise ValueError('Non-regular metadata')
            data=bytearray()
            while len(data)<=limit:
                chunk=os.read(fd,min(4096,limit+1-len(data)))
                if not chunk:break
                data.extend(chunk)
            if len(data)>limit:raise ValueError('Metadata limit exceeded')
            return bytes(data)
        finally:os.close(fd)
    def current():
        if metadata(boot_path,128).decode().strip()!=expected_boot:
            raise ValueError('Boot changed')
        raw=metadata(checkpoint,1024*1024)
        if hashlib.sha256(raw).hexdigest()!=expected_checkpoint:
            raise ValueError('Checkpoint changed')
        c=json.loads(raw)
        if c.get('boot_id')!=expected_boot or c.get('active') is not False:
            raise ValueError('Checkpoint is not freshly inactive')
        for k in ['user_attention_hold','cooling_only']:
            if c.get(k): raise ValueError('Independent hold: '+k)
        for k in ['user_pause','migration_hold']:
            if c.get(k,{}).get('active'): raise ValueError('Independent hold: '+k)
        hold=c.get('camera_operation_hold',{})
        if hold.get('active'):
            if (purpose!='restoration_material' or
                not isinstance(restoration_session,str) or not re.fullmatch('[a-f0-9]{32}',restoration_session) or
                c.get('phase') not in ('independent_pre_capture_restoration_hold','independent_post_capture_controls_restoration_hold') or
                hold.get('failed_session')!=restoration_session):
                raise ValueError('Camera hold permits only bound inactive restoration material')
        return c
    sample=current()
    # Atomic reservation; never replace an old package or follow a symlink.
    destination.mkdir(mode=0o755)
    created=[]
    try:
        destination.chmod(0o755)
        manifest={k:hashlib.sha256(v).hexdigest() for k,v in files.items()}
        contents={**files,'manifest.json':(json.dumps(manifest,sort_keys=True)+'\n').encode(),
          'receipt.json':(json.dumps({'boot_id':expected_boot,'checkpoint_sha256':expected_checkpoint,
              'manifest':manifest,'camera_started':False,'modules_loaded':False,
              'rights_added':False,'RAM_only':True,'purpose':purpose,'capture_authorized':False,'camera_hold_preserved':sample.get('camera_operation_hold',{}).get('active',False)},sort_keys=True)+'\n').encode()}
        for name,data in contents.items():
            fd=os.open(destination/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            created.append(name)
            with os.fdopen(fd,'wb') as f:
                f.write(data);f.flush();os.fsync(f.fileno())
                os.fchmod(f.fileno(),0o755 if name in EXECUTABLES else 0o444)
        current()
        fd=os.open(destination,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(fd)
        finally:os.close(fd)
        return {'staged':True,'manifest':manifest,'modules_loaded':False}
    except BaseException:
        # Remove only files this invocation created. An unrelated entry prevents
        # directory removal and is preserved, never swept recursively.
        for name in created:
            (destination/name).unlink()
        destination.rmdir()
        raise
