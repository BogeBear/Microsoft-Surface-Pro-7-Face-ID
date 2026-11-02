# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded root-peer diagnostic IPC. No camera or authentication operation.

There is no daemon entry point, service installer or PAM connection in this
module. The only valid response is backend_unavailable/password fallback.
SO_PEERCRED authenticates the local Unix peer, not a biometric assertion.
"""
from pathlib import Path
import json
import os
import re
import socket
import stat
import struct
import time
import uuid

MAX_FRAME=1024
IO_BUDGET=.25
MAX_AGE_NS=2_000_000_000
REQUEST_KEYS={'schema','operation','service','uid','nonce','boot','issued_ns'}
REPLY_KEYS={'schema','service','uid','nonce','boot','status','authentication_allowed','password_fallback'}


def root_peer(s):
    if s.family!=socket.AF_UNIX:raise ValueError('Unix socket required')
    pid,uid,gid=struct.unpack('3i',s.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
    if pid<=0 or uid!=0:raise ValueError('unqualified local peer')
    return pid,uid,gid


def remaining(deadline):
    left=deadline-time.monotonic()
    if left<=0:raise TimeoutError('diagnostic deadline')
    return min(left,IO_BUDGET)


def encode(value):
    data=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n'
    if len(data)>MAX_FRAME:raise ValueError('frame budget')
    return data


def decode(data):
    if type(data) is not bytes or len(data)>MAX_FRAME or not data.endswith(b'\n') or data.count(b'\n')!=1:
        raise ValueError('invalid diagnostic frame')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('duplicate JSON key')
            result[key]=value
        return result
    def constant(_):raise ValueError('nonfinite JSON')
    value=json.loads(data,object_pairs_hook=pairs,parse_constant=constant)
    if type(value) is not dict:raise ValueError('object required')
    return value


def read_frame(s,deadline):
    # Require write-half-close. This rejects trailing/pipelined data rather
    # than accepting a prefix while ignoring later bytes on the connection.
    chunks=[];count=0
    while True:
        s.settimeout(remaining(deadline));part=s.recv(min(256,MAX_FRAME+1-count))
        if not part:return decode(b''.join(chunks))
        chunks.append(part);count+=len(part)
        if count>MAX_FRAME:raise ValueError('frame budget')


def send_frame(s,value,deadline):
    s.settimeout(remaining(deadline));s.sendall(encode(value));s.shutdown(socket.SHUT_WR)


class Policy:
    """In-memory, one-owner diagnostic policy; no production users by default."""
    def __init__(self,boot,eligible_uids=frozenset()):
        if type(boot) is not str or str(uuid.UUID(boot))!=boot:raise ValueError('invalid boot')
        self.boot=boot;self.uids=frozenset(eligible_uids);self.used={}
        if len(self.uids)>128 or any(type(u) is not int or not 1000<=u<2**32 for u in self.uids):
            raise ValueError('invalid account policy')
    def claim(self,r,now_ns):
        if type(r) is not dict or set(r)!=REQUEST_KEYS:raise ValueError('request schema')
        if (type(r['schema']) is not int or r['schema']!=1 or r['operation']!='diagnostic' or
                r['service']!='sddm' or type(r['uid']) is not int or r['uid'] not in self.uids or
                r['boot']!=self.boot or type(r['nonce']) is not str or
                not re.fullmatch('[0-9a-f]{64}',r['nonce']) or type(r['issued_ns']) is not int or
                not 0<=r['issued_ns']<2**63 or type(now_ns) is not int or
                not 0<=now_ns-r['issued_ns']<=MAX_AGE_NS):
            raise ValueError('unqualified request')
        self.used={n:t for n,t in self.used.items() if now_ns-t<=MAX_AGE_NS}
        if r['nonce'] in self.used or len(self.used)>=256:raise ValueError('replay or request budget')
        self.used[r['nonce']]=now_ns


def serve_connection(conn,policy):
    """Own and always close a single accepted socket. No retry or subprocess."""
    try:
        if os.geteuid()!=0:raise ValueError('root server role required')
        root_peer(conn);deadline=time.monotonic()+IO_BUDGET
        request=read_frame(conn,deadline);policy.claim(request,time.monotonic_ns())
        response={k:request[k] for k in ('schema','service','uid','nonce','boot')}
        response.update(status='backend_unavailable',authentication_allowed=False,password_fallback=True)
        send_frame(conn,response,deadline)
        return True
    except (OSError,ValueError,TypeError,KeyError,OverflowError):
        return False
    finally:
        conn.close()


def fallback(reason):
    return dict(authentication_allowed=False,password_fallback=True,reason=reason,
                camera_started=False,transport_verified=False)


def exchange_connected(conn,request,deadline):
    """Internal connected-socket check; file-path trust is checked by client()."""
    try:
        if os.geteuid()!=0:raise ValueError('root client role required')
        root_peer(conn)
        send_frame(conn,request,deadline);reply=read_frame(conn,deadline)
        if set(reply)!=REPLY_KEYS or any(reply[k]!=request[k] for k in ('schema','service','uid','nonce','boot')):
            raise ValueError('response binding')
        if (type(reply['schema']) is not int or type(reply['uid']) is not int or
                reply['status']!='backend_unavailable' or reply['authentication_allowed'] is not False or
                reply['password_fallback'] is not True):
            raise ValueError('invalid diagnostic response')
        return dict(fallback('backend_unavailable'),transport_verified=True)
    except (OSError,ValueError,TypeError,KeyError,OverflowError):
        return fallback('unavailable_or_unverified_transport')
    finally:
        conn.close()


def trusted_socket(path):
    """Require a root-only final directory/socket; refuse symlinks/replacement.

    This is a diagnostic root-to-root channel. The future service must also
    retain root ownership of its executable/config and must not delegate its
    listening/accepted descriptors to unqualified processes.
    """
    p=Path(path)
    if not p.is_absolute() or len(os.fsencode(p))>100:raise ValueError('socket path')
    parent=p.parent.lstat();node=p.lstat()
    if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid!=0 or stat.S_IMODE(parent.st_mode)!=0o700 or
            not stat.S_ISSOCK(node.st_mode) or node.st_uid!=0 or stat.S_IMODE(node.st_mode)!=0o600):
        raise ValueError('untrusted diagnostic socket')
    return (parent.st_dev,parent.st_ino,node.st_dev,node.st_ino)


def client(path,request):
    if os.geteuid()!=0:return fallback('unqualified_client_role')
    deadline=time.monotonic()+IO_BUDGET;s=None
    try:
        if type(request) is not dict:raise ValueError('request object required')
        request=dict(request)
        Policy(request['boot'],{request['uid']}).claim(request,time.monotonic_ns())
        before=trusted_socket(path)
        s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);s.settimeout(remaining(deadline));s.connect(str(path))
        if before!=trusted_socket(path):raise ValueError('socket replaced')
        return exchange_connected(s,request,deadline)
    except (OSError,ValueError,TypeError,KeyError,OverflowError):
        if s is not None:s.close()
        return fallback('unavailable_or_unverified_transport')
