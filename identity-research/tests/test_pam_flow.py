# SPDX-License-Identifier: GPL-3.0-or-later
"""Real libpam control-flow tests in a disposable VM, synthetic modules only.

Never invokes /etc/pam.d, a real password module, account database or camera.
"""
from pathlib import Path
import os, subprocess, tempfile, unittest

BASE=Path(os.environ.get('SP7_PAM_TEST_BASE','/opt/id-test')).resolve()
SUCCESS,AUTH_ERR,UNAVAILABLE,IGNORE=0,7,9,25


def driver_command(conf,service,expected):
    loader=BASE/'lib/ld-linux-x86-64.so.2'
    prefix=[str(loader),'--library-path',str(BASE/'lib')] if loader.is_file() else []
    return [*prefix,str(BASE/'pam_driver'),str(conf),service,str(expected)]


class PamFlow(unittest.TestCase):
    def fixture(self, *, actual=False, factor=IGNORE, unix=SUCCESS, homed=IGNORE,
                preauth=SUCCESS,shells=SUCCESS,nologin=SUCCESS,env=SUCCESS,
                account=SUCCESS,service='sddm',insert=True):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        conf=Path(self.temp.name);trace=conf/'trace'
        def module(tag,ret):return f'{BASE}/pam_trace.so {trace} {tag} {ret}'
        factorline=f'auth [success=3 default=ignore] {BASE}/pam_sp7_research.so' if actual else f'auth [success=3 default=ignore] {module("face",factor)}'
        auth=[f'auth required {module("preauth",preauth)}']
        if insert:auth.append(factorline)
        auth += [f'auth [success=2 default=ignore] {module("homed",homed)}',
                 f'auth [success=1 default=bad] {module("unix",unix)}',
                 f'auth [default=die] {module("authfail",AUTH_ERR)}',
                 f'auth optional {module("permit",SUCCESS)}',
                 f'auth required {module("env",env)}',
                 f'auth required {module("authsucc",SUCCESS)}',
                 f'account required {module("account",account)}']
        (conf/'system-auth').write_text('\n'.join(auth)+'\n')
        (conf/'system-login').write_text(f'auth required {module("shells",shells)}\nauth requisite {module("nologin",nologin)}\nauth include system-auth\naccount include system-auth\n')
        (conf/service).write_text(f'auth include system-login\nauth optional {module("wallet",SUCCESS)}\naccount include system-login\n')
        return conf,trace
    def check(self,expected,**kwargs):
        conf,trace=self.fixture(**kwargs)
        r=subprocess.run(driver_command(conf,kwargs.get('service','sddm'),expected),capture_output=True,text=True,timeout=5)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        values=list(map(int,r.stdout.split()))
        return values,trace.read_text().splitlines() if trace.exists() else []
    def test_diagnostic_module_cannot_bypass_password(self):
        for service in ('sddm','kde','sshd'):
            for password,expected in ((SUCCESS,SUCCESS),(AUTH_ERR,AUTH_ERR)):
                with self.subTest(service=service,password=password):
                    values,trace=self.check(expected,actual=True,unix=password,service=service)
                    self.assertIn('unix',trace)
                    if password==SUCCESS:self.assertEqual(values,[0,0,0,0])
    def test_password_fallback_preserves_exact_auth_path(self):
        for password,expected in ((SUCCESS,SUCCESS),(AUTH_ERR,AUTH_ERR)):
            _,baseline=self.check(expected,insert=False,unix=password)
            _,candidate=self.check(expected,actual=True,unix=password)
            self.assertEqual(baseline,candidate)
    def test_all_factor_errors_fall_back(self):
        for factor in (IGNORE,UNAVAILABLE,AUTH_ERR,4,19,26):
            for password,expected in ((SUCCESS,SUCCESS),(AUTH_ERR,AUTH_ERR)):
                with self.subTest(factor=factor,password=password):
                    _,trace=self.check(expected,factor=factor,unix=password)
                    self.assertIn('unix',trace)
    def test_synthetic_factor_success_skips_only_password_alternatives(self):
        values,trace=self.check(SUCCESS,factor=SUCCESS,unix=AUTH_ERR)
        self.assertEqual(values,[0,0,0,0])
        self.assertEqual(trace,['shells','nologin','preauth','face','permit','env','authsucc','wallet','account'])
    def test_required_lockout_survives_synthetic_factor_success(self):
        _,trace=self.check(AUTH_ERR,factor=SUCCESS,preauth=AUTH_ERR)
        self.assertIn('env',trace);self.assertIn('authsucc',trace)
        self.assertNotIn('unix',trace)
    def test_shell_policy_survives_synthetic_factor_success(self):
        self.check(AUTH_ERR,factor=SUCCESS,shells=AUTH_ERR)
    def test_nologin_requisite_stops_before_factor(self):
        _,trace=self.check(AUTH_ERR,factor=SUCCESS,nologin=AUTH_ERR)
        self.assertEqual(trace,['shells','nologin'])
    def test_required_env_survives_synthetic_factor_success(self):
        self.check(AUTH_ERR,factor=SUCCESS,env=AUTH_ERR)
    def test_original_homed_jump_still_works(self):
        _,trace=self.check(SUCCESS,factor=IGNORE,homed=SUCCESS,unix=AUTH_ERR)
        self.assertNotIn('unix',trace);self.assertNotIn('authfail',trace)
        self.assertIn('env',trace);self.assertIn('authsucc',trace)
    def test_account_denial_cannot_be_authorized_by_factor(self):
        values,_=self.check(SUCCESS,factor=SUCCESS,account=AUTH_ERR)
        self.assertEqual(values[2],AUTH_ERR)
    def test_unix_failure_still_reaches_lockout_authfail(self):
        _,trace=self.check(AUTH_ERR,factor=IGNORE,unix=AUTH_ERR)
        self.assertEqual(trace[-1],'authfail')
        self.assertNotIn('authsucc',trace)
    def test_top_level_sufficient_would_skip_required_downstream_policy(self):
        # Demonstrate why this easier placement is excluded from our proposal.
        conf,trace=self.fixture(shells=AUTH_ERR,preauth=AUTH_ERR)
        s=conf/'sddm'
        s.write_text(f'auth sufficient {BASE}/pam_trace.so {trace} unsafe-top-factor 0\n'+s.read_text())
        r=subprocess.run(driver_command(conf,'sddm',0),capture_output=True,text=True,timeout=5)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        lines=trace.read_text().splitlines()
        self.assertNotIn('shells',lines);self.assertNotIn('preauth',lines)
        self.assertEqual(lines,['unsafe-top-factor','account'])
    def test_disabled_module_has_no_arguments_or_activation_flag(self):
        source_path=BASE/'pam_sp7_research.c'
        if not source_path.is_file():source_path=Path(__file__).resolve().parents[1]/'src/pam_sp7_research.c'
        source=source_path.read_text()
        self.assertNotIn('return PAM_SUCCESS;',source.split('pam_sm_setcred')[0])
        self.assertNotIn('PAM_AUTHTOK',source)
        self.assertNotIn('pam_get_user(',source.replace('/* Do not call pam_get_user:', '/*'))


if __name__=='__main__':unittest.main()
