# SPDX-License-Identifier: GPL-3.0-or-later
import hashlib,unittest
from pam_layout import parse,graph,proposal


AUTH='''# Synthetic reviewed fixture
auth required pam_faillock.so preauth
-auth [success=2 default=ignore] pam_systemd_home.so
auth [success=1 default=bad] pam_unix.so try_first_pass nullok
auth [default=die] pam_faillock.so authfail
auth optional pam_permit.so
auth required pam_env.so
auth required pam_faillock.so authsucc
account required pam_unix.so
password required pam_unix.so
session required pam_unix.so
'''


class Tests(unittest.TestCase):
    def inputs(self):
        files={'system-auth':AUTH,'sddm':'auth include system-login\naccount include system-login\npassword include system-login\nsession include system-login\n',
               'kde':'auth include system-login\n','system-login':'auth include system-auth\naccount include system-auth\npassword include system-auth\nsession include system-auth\n'}
        hashes={k:hashlib.sha256(v.encode()).hexdigest() for k,v in files.items()}
        return files,hashes
    def test_proposal_inactive_and_original_bytes_preserved(self):
        f,h=self.inputs();p=proposal(f,h,'a'*64)
        self.assertFalse(p['activation_allowed'])
        self.assertTrue(p['read_only'])
        line='auth [success=3 default=ignore] /usr/lib/security/pam_sp7_research.so\n'
        self.assertEqual(p['proposed_system_auth'].replace(line,''),AUTH)
        self.assertEqual(f['system-auth'],AUTH)
    def test_changed_file_refused_even_if_change_seems_harmless(self):
        f,h=self.inputs();f['sddm']+='\n'
        with self.assertRaises(ValueError):proposal(f,h,'a'*64)
    def test_new_module_or_reordered_control_needs_new_profile(self):
        f,h=self.inputs();f['system-auth']=f['system-auth'].replace('auth required pam_env.so','auth sufficient pam_env.so')
        h['system-auth']=hashlib.sha256(f['system-auth'].encode()).hexdigest()
        with self.assertRaises(ValueError):proposal(f,h,'a'*64)
    def test_missing_include_refused(self):
        with self.assertRaises(ValueError):graph({'sddm':'auth include absent'},'sddm')
    def test_cycles_refused(self):
        with self.assertRaises(ValueError):graph({'a':'auth include b','b':'auth include a'},'a')
    def test_traversal_and_unknown_syntax_refused(self):
        for text in ('auth include ../bad','@include system-auth','auth nope x','auth required x\\\ny','auth required x\x00'):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):parse(text)
    def test_account_includes_separate_from_auth(self):
        edges,modules=graph({'a':'auth required face\naccount include b','b':'account required policy'},'a','account')
        self.assertEqual(edges,[('a','b','include')]);self.assertEqual(modules[0][1].module,'policy')
    def test_substack_semantics_retained_not_flattened_into_auth_recipe(self):
        edges,_=graph({'a':'auth substack b','b':'auth required x'},'a')
        self.assertEqual(edges,[('a','b','substack')])
    def test_budget_refuses_exponential_graph(self):
        f={'n0':'auth required x'}
        for i in range(1,11):f['n'+str(i)]=f'auth include n{i-1}\nauth include n{i-1}'
        with self.assertRaises(ValueError):graph(f,'n10')
    def test_unknown_or_malformed_module_pin_refused(self):
        f,h=self.inputs()
        for pin in ('','a'*63,'x'*64):
            with self.assertRaises(ValueError):proposal(f,h,pin)


if __name__=='__main__':unittest.main()
