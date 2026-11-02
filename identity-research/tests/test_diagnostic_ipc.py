# SPDX-License-Identifier: GPL-3.0-or-later
"""Root/UID role tests execute only in the isolated VM; no real service/PAM."""
from pathlib import Path
import json,multiprocessing as mp,os,socket,tempfile,time,unittest,uuid
import diagnostic_ipc as ipc

BOOT='b29da3f6-41b1-4cb1-891c-d2061589bbaa'
def request(**changes):
    r=dict(schema=1,operation='diagnostic',service='sddm',uid=1000,
           nonce='a'*64,boot=BOOT,issued_ns=time.monotonic_ns())
    r.update(changes);return r


class PolicyTests(unittest.TestCase):
    def test_default_policy_never_enables_accounts(self):
        with self.assertRaises(ValueError):ipc.Policy(BOOT).claim(request(),time.monotonic_ns())
    def test_role_schema_clock_and_binding_rejected(self):
        changes=[dict(schema=True),dict(uid=True),dict(uid=0),dict(uid=1001),dict(uid=2**32),
                 dict(service='kde'),dict(service='sshd'),dict(operation='capture'),dict(boot=str(uuid.uuid4())),
                 dict(nonce='a'*63),dict(nonce='g'*64),dict(issued_ns=True),dict(issued_ns=-1),
                 dict(issued_ns=time.monotonic_ns()+10**12),dict(issued_ns=time.monotonic_ns()-3*10**9),
                 dict(password='synthetic-unused'),dict(path='/synthetic-no-file-read')]
        for change in changes:
            with self.subTest(change=change):
                with self.assertRaises(ValueError):ipc.Policy(BOOT,{1000}).claim(request(**change),time.monotonic_ns())
    def test_nonce_consumed_and_budget_bounded(self):
        p=ipc.Policy(BOOT,{1000});r=request();now=r['issued_ns'];p.claim(r,now)
        with self.assertRaises(ValueError):p.claim(r,now)
        for i in range(1,256):p.claim(request(nonce=f'{i:064x}',issued_ns=now),now)
        with self.assertRaises(ValueError):p.claim(request(nonce='f'*64,issued_ns=now),now)
        p.claim(request(nonce='f'*64,issued_ns=now+ipc.MAX_AGE_NS+1),now+ipc.MAX_AGE_NS+1)
        self.assertEqual(len(p.used),1)
    def test_duplicate_nonfinite_trailing_or_oversize_json_rejected(self):
        for data in (b'{"schema":1,"schema":1}\n',b'{"x":NaN}\n',b'[]\n',b'{}\n{}\n',b'{}',b'a'*1025):
            with self.subTest(data=data[:30]):
                with self.assertRaises(ValueError):ipc.decode(data)
    def test_wire_roundtrip_and_budget(self):
        r=request();self.assertEqual(ipc.decode(ipc.encode(r)),r)
        with self.assertRaises(ValueError):ipc.encode({'large':'x'*1024})
    def test_other_socket_family_rejected_without_network(self):
        class Fake:family=socket.AF_INET
        with self.assertRaises(ValueError):ipc.root_peer(Fake())
    def test_fallback_does_not_claim_camera_shutdown_or_authentication(self):
        r=ipc.fallback('test');self.assertIs(r['authentication_allowed'],False)
        self.assertIs(r['password_fallback'],True);self.assertIs(r['camera_started'],False)
        self.assertNotIn('shutdown_confirmed',r)
    @unittest.skipIf(os.geteuid()==0,'nonroot role exercised by ordinary-user VM run')
    def test_nonroot_client_refuses_without_connecting(self):
        r=ipc.client('/this-synthetic-path-is-never-opened',request())
        self.assertEqual(r['reason'],'unqualified_client_role')


@unittest.skipUnless(os.geteuid()==0,'root peer integration requires disposable root VM')
class RootTransportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'diagnostic.sock';self.children=[]
        self.addCleanup(self.close_children)
    def close_children(self):
        for p in self.children:
            p.join(1)
            if p.is_alive():p.terminate();p.join(1)
            self.assertFalse(p.is_alive())
    def child(self,fn,*args):
        p=mp.get_context('fork').Process(target=fn,args=args);p.start();self.children.append(p);return p
    def listener(self,mode=0o600):
        s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);s.bind(str(self.path));os.chmod(self.path,mode);s.listen(2);s.settimeout(2);self.addCleanup(s.close);return s
    def root_server(self,count=1,reply=None,stall=False):
        listener=self.listener()
        def serve():
            policy=ipc.Policy(BOOT,{1000})
            for _ in range(count):
                conn,_=listener.accept()
                if stall:
                    time.sleep(.7);conn.close()
                elif reply is not None:
                    try:
                        deadline=time.monotonic()+1;r=ipc.read_frame(conn,deadline)
                        response={k:r[k] for k in ('schema','uid','nonce','boot','service')}
                        response.update(status='backend_unavailable',authentication_allowed=False,password_fallback=True)
                        response.update(reply);ipc.send_frame(conn,response,deadline)
                    finally:conn.close()
                else:ipc.serve_connection(conn,policy)
            listener.close()
        self.child(serve);return listener
    def test_actual_root_peer_exchange_only_reports_unavailable(self):
        self.root_server();r=ipc.client(self.path,request())
        self.assertTrue(r['transport_verified']);self.assertEqual(r['reason'],'backend_unavailable')
        self.assertIs(r['authentication_allowed'],False);self.assertIs(r['password_fallback'],True)
    def test_same_nonce_cannot_be_replayed(self):
        self.root_server(count=2);req=request()
        self.assertTrue(ipc.client(self.path,req)['transport_verified'])
        self.assertFalse(ipc.client(self.path,req)['transport_verified'])
    def test_stalled_peer_returns_password_within_bound(self):
        self.root_server(stall=True);start=time.monotonic();r=ipc.client(self.path,request())
        self.assertFalse(r['transport_verified']);self.assertTrue(r['password_fallback'])
        self.assertLess(time.monotonic()-start,.8)
    def test_root_peer_cannot_inject_success(self):
        self.root_server(reply=dict(status='accepted',authentication_allowed=True,password_fallback=False))
        r=ipc.client(self.path,request());self.assertFalse(r['transport_verified'])
        self.assertFalse(r['authentication_allowed'])
    def test_wrong_response_binding_rejected(self):
        self.root_server(reply=dict(nonce='b'*64));r=ipc.client(self.path,request())
        self.assertFalse(r['transport_verified'])
    def test_truthy_response_booleans_rejected(self):
        self.root_server(reply=dict(authentication_allowed=0,password_fallback=1));r=ipc.client(self.path,request())
        self.assertFalse(r['transport_verified'])
    def test_socket_permissions_and_symlink_refused(self):
        self.listener(mode=0o666)
        with self.assertRaises(ValueError):ipc.trusted_socket(self.path)
        os.chmod(self.path,0o600);link=self.path.parent/'link.sock';link.symlink_to(self.path.name)
        with self.assertRaises(ValueError):ipc.trusted_socket(link)
        os.chmod(self.path.parent,0o755)
        with self.assertRaises(ValueError):ipc.trusted_socket(self.path)
    def test_unprivileged_server_rejected_before_request_bytes(self):
        os.chmod(self.path.parent,0o777);ready_rx,ready_tx=mp.Pipe(duplex=False);data_rx,data_tx=mp.Pipe(duplex=False)
        def serve():
            os.setgroups([]);os.setgid(1000);os.setuid(1000)
            listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);listener.bind(str(self.path));listener.listen(1);listener.settimeout(2);ready_tx.send(True)
            conn,_=listener.accept();conn.settimeout(1)
            try:data_tx.send(len(conn.recv(1024)))
            finally:conn.close();listener.close()
        self.child(serve);self.assertTrue(ready_rx.poll(2));self.assertTrue(ready_rx.recv())
        conn=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);conn.connect(str(self.path))
        r=ipc.exchange_connected(conn,request(),time.monotonic()+ipc.IO_BUDGET)
        self.assertFalse(r['transport_verified']);self.assertTrue(data_rx.poll(2));self.assertEqual(data_rx.recv(),0)
    def test_unprivileged_client_is_rejected_by_kernel_peer_credentials(self):
        os.chmod(self.path.parent,0o777);listener=self.listener(mode=0o666)
        def connect():
            os.setgroups([]);os.setgid(1000);os.setuid(1000)
            conn=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);conn.settimeout(1);conn.connect(str(self.path))
            try:
                try:conn.sendall(ipc.encode(request()));conn.shutdown(socket.SHUT_WR);conn.recv(1024)
                except OSError:pass
            finally:conn.close()
        self.child(connect);conn,_=listener.accept();self.assertFalse(ipc.serve_connection(conn,ipc.Policy(BOOT,{1000})))
    def test_stalled_partial_client_does_not_hang_server(self):
        listener=self.listener()
        def connect():
            conn=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);conn.connect(str(self.path));conn.sendall(b'{');time.sleep(.7);conn.close()
        self.child(connect);conn,_=listener.accept();start=time.monotonic()
        self.assertFalse(ipc.serve_connection(conn,ipc.Policy(BOOT,{1000})))
        self.assertLess(time.monotonic()-start,.8)


if __name__=='__main__':unittest.main()
