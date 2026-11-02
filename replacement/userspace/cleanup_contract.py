# SPDX-License-Identifier: GPL-3.0-only
"""Delete only exact hash/fsync-acknowledged private session RAM files.
No camera/illumination operation, recursion, backup deletion or hold clearing.
"""
from pathlib import Path
import hashlib,os,re,stat
from ram_stage import ram_filesystem

def cleanup(directory,expected,io,profile='restored_failed_trial'):
    result={'complete':False,'removed':[],'errors':[]}
    try:
        p=Path(directory)
        if os.geteuid()!=0 or not re.fullmatch(r'/run/sp7-ir-metadata-[a-f0-9]{32}',str(p)):raise ValueError('Fixed private RAM session required')
        for parent in [p,*p.parents]:
            s=parent.lstat()
            if not stat.S_ISDIR(s.st_mode) or s.st_uid!=0 or s.st_mode&0o022:raise ValueError('Unprotected directory: '+str(parent))
        if p.stat().st_mode&0o777!=0o700 or not ram_filesystem(p):raise ValueError('Private RAM directory required: mode='+oct(p.stat().st_mode&0o777)+',ram='+str(ram_filesystem(p)))
        inventories={'restored_failed_trial':{'ir.raw','rgb.raw',*[f'format-{i}.bin' for i in range(24)]},'raw_after_verified_teardown':{'ir.raw','rgb.raw'}}
        if profile not in inventories or set(expected)!=inventories[profile]:raise ValueError('Exact completed session inventory/profile required')
        for name,row in expected.items():
            if set(row)!={'size','sha256','uid','fsynced_backup'} or row['fsynced_backup'] is not True or not re.fullmatch('[a-f0-9]{64}',row['sha256']) or not 0<row['size']<=302330880 or row['uid']!=(1000 if name.endswith('.raw') else 0):raise ValueError('Invalid export acknowledgement')
        io.guard();result['before']=io.full_idle()
        if {x.name for x in p.iterdir()}!=set(expected):raise ValueError('Session inventory changed')
        identities={}
        for name,row in expected.items():
            fd=os.open(p/name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK)
            try:
                s=os.fstat(fd)
                if not stat.S_ISREG(s.st_mode) or s.st_uid!=row['uid'] or s.st_nlink!=1 or s.st_mode&0o777!=(0o600 if name.endswith('.raw') else 0o644) or s.st_size!=row['size']:raise ValueError('Unexpected session file: '+name)
                h=hashlib.sha256();remaining=s.st_size
                while remaining:
                    block=os.read(fd,min(1048576,remaining))
                    if not block:raise ValueError('Truncated session file')
                    h.update(block);remaining-=len(block)
                identity=lambda x:(x.st_dev,x.st_ino,x.st_size,x.st_mtime_ns,x.st_ctime_ns,x.st_uid,x.st_mode)
                identities[name]=identity(s)
                if h.hexdigest()!=row['sha256'] or identity(os.fstat(fd))!=identities[name]:raise ValueError('Session file changed or hash mismatch')
            finally:os.close(fd)
        io.guard()
        if {x.name for x in p.iterdir()}!=set(expected):raise ValueError('Session inventory changed before removal')
        for name in sorted(expected):
            io.before_unlink(p/name)
            if identity((p/name).lstat())!=identities[name]:raise ValueError('Session file changed before unlink')
            (p/name).unlink();result['removed'].append(name)
        p.rmdir();result['after']=io.full_idle();result['complete']=True
    except BaseException as error:result['errors'].append(type(error).__name__+': '+str(error))
    result['capture_authorized']=False;result['external_root_exit_required']=True
    return result
