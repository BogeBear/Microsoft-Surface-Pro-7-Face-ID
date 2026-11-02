# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline PAM layout proposal. No filesystem writer, install or apply action."""
from dataclasses import dataclass
import hashlib
import re

NAME=re.compile(r'[A-Za-z0-9_-]{1,64}\Z')
LINE=re.compile(r'^(-?)(auth|account|password|session)\s+(\[[^\]\n]+\]|[a-z]+)\s+(\S+)(?:\s+(.*))?$')


@dataclass(frozen=True)
class Line:
    kind: str
    control: str
    module: str
    arguments: tuple[str, ...]
    original_line: int


def parse(text):
    if type(text) is not str or '\x00' in text or '\\' in text or len(text.encode())>65536:
        raise ValueError('unsupported PAM text')
    rows=[]
    for number,line in enumerate(text.splitlines(),1):
        s=line.strip()
        if not s or s.startswith('#'):continue
        m=LINE.fullmatch(s)
        if not m:raise ValueError('unsupported PAM syntax')
        _,kind,control,module,args=m.groups()
        if control not in ('required','requisite','sufficient','optional','include','substack') and not control.startswith('['):
            raise ValueError('unknown control')
        if control in ('include','substack') and (not NAME.fullmatch(module) or args):
            raise ValueError('unsupported include')
        rows.append(Line(kind,control,module,tuple((args or '').split()),number))
    if len(rows)>256:raise ValueError('PAM line budget')
    return rows


def graph(files, service, kind='auth'):
    if type(files) is not dict or len(files)>32 or kind not in ('auth','account','password','session'):
        raise ValueError('graph budget or kind')
    parsed={}
    for name,text in files.items():
        if not isinstance(name,str) or not NAME.fullmatch(name):raise ValueError('invalid service name')
        parsed[name]=parse(text)
    edges=[];modules=[]
    def visit(name,path):
        if name in path or len(path)>=12 or name not in parsed:raise ValueError('cycle, depth or missing include')
        for row in parsed[name]:
            if row.kind!=kind:continue
            if row.control in ('include','substack'):
                edges.append((name,row.module,row.control))
                visit(row.module,(*path,name))
            else:modules.append((name,row))
            if len(edges)+len(modules)>512:raise ValueError('expanded graph budget')
    visit(service,())
    return edges,modules


def proposal(files, reviewed_hashes, module_sha256):
    """Bind a read-only proposal to externally reviewed exact file bytes.

    This does not trust a caller's review hash as installation authorization.
    No apply operation exists. Ownership/mode/package checks are separate live
    deployment requirements and cannot be inferred from these text strings.
    """
    if set(files)!=set(reviewed_hashes) or not re.fullmatch('[0-9a-f]{64}',module_sha256):
        raise ValueError('unbound input')
    actual={k:hashlib.sha256(v.encode()).hexdigest() for k,v in files.items()}
    if actual!=reviewed_hashes:raise ValueError('reviewed file changed')
    for service in ('sddm','kde'):
        for kind in ('auth','account','password','session'):graph(files,service,kind)
    auth=[row for row in parse(files['system-auth']) if row.kind=='auth']
    expected=[('required','pam_faillock.so',('preauth',)),
              ('[success=2 default=ignore]','pam_systemd_home.so',()),
              ('[success=1 default=bad]','pam_unix.so',('try_first_pass','nullok')),
              ('[default=die]','pam_faillock.so',('authfail',)),
              ('optional','pam_permit.so',()),('required','pam_env.so',()),
              ('required','pam_faillock.so',('authsucc',))]
    if [(r.control,r.module,r.arguments) for r in auth]!=expected:
        raise ValueError('auth stack is not the reviewed profile')
    # Preserve every original byte; insert a proposal line before homed only.
    original=files['system-auth'].splitlines(keepends=True)
    at=auth[1].original_line-1
    proposed=original[:at]+['auth [success=3 default=ignore] /usr/lib/security/pam_sp7_research.so\n']+original[at:]
    return dict(schema=1,profile='inactive-diagnostic-only',activation_allowed=False,
        authentication_backend_available=False,read_only=True,module_sha256=module_sha256,
        original_sha256=actual,proposed_system_auth=''.join(proposed),
        requires_live_owner_mode_package_and_password_recovery_verification=True,
        affects_shared_system_auth=True,all_other_files_unchanged=True)
