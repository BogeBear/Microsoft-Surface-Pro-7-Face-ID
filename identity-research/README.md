# Inactive Manjaro identity-integration research

This directory contains a testable attempt contract and a diagnostic-only PAM
module. **It does not recognize identities or authorize authentication.** No
production PAM file, account, service, privilege policy or camera is changed.

The attempt contract consumes a one-use boot/account/service-bound challenge,
requires fresh complete evidence, and attempts full shutdown even if acquisition
fails. Restoration is not attempted after an unconfirmed native/kernel/root
stop. Final idle, exact restoration and a fresh noncancelled deadline are needed
even for a synthetic research-eligible result. All results require a password.
There is no production camera or identity adapter and no trusted evidence IPC.

The diagnostic PAM module always returns `PAM_IGNORE` from authentication. Its
credential callback creates no credentials. It has no enable switch, password
conversation, template reader, socket, camera or success path. Root is required
even to enter its diagnostic branch; the actual KDE lock-screen caller role
still needs qualification. Installing this module would provide no face login.

## Actual configuration findings

Read-only SP7 inspection found Manjaro PAM 1.7.2-2, SDDM 0.21.0-7 and Plasma
workspace 6.7.4-3. SDDM includes `system-login`, then `system-auth`. KDE uses a
vendor fallback in `/usr/lib/pam.d/kde`, including `system-local-login` and then
the same stack. `/etc/pam.d/kde` is absent. The exact diagnostic snapshots remain
private evidence, not installation inputs.

A top-level `auth sufficient` insertion can bypass downstream shell, nologin,
lockout or environment policy. The VM tests instead exercise a **proposal**, not
an installation instruction: an ignored-by-default factor after the required
lockout precheck, with a successful synthetic factor skipping only the three
password-alternative/authfail entries. Required environment and lockout-success
modules still run. The original homed and Unix jumps retain their targets.
Account management is separately required. All factor errors use password flow.

This is not enough to enable authentication. Production integration still needs
fresh fingerprints of every selected PAM file and package, bounded authenticated
IPC, caller-role and account eligibility rules, a qualified identity and PAD
backend, calibrated RGB/IR geometry and clocks, complete camera closure, verified
real password recovery and a tested rollback. The global `system-auth` file is
shared by other services; copying a snapshot also risks missing security updates.
No such change is applied by this work. KWallet remains untouched; passwordless
authentication cannot supply its missing password automatically.

## Validation

The C fixture is deliberately unsafe synthetic test code and is never an
installable authentication module. Tests use `pam_start_confdir` with isolated
temporary files, fake module return values and a synthetic account name. They
never call a real password backend, read password hashes or modify `/etc/pam.d`.
The disposable VM has no network, host mounts or device passthrough. Native
fixtures are built on the development host and executed in that VM only.

Linux-PAM primary references:

- https://github.com/linux-pam/linux-pam/blob/master/doc/man/pam.conf-syntax.xml
- https://github.com/linux-pam/linux-pam/blob/master/doc/man/pam_sm_authenticate.3.xml
- https://github.com/linux-pam/linux-pam/blob/master/doc/man/pam_sm_setcred.3.xml

No face images, embeddings, identity templates, passwords or private keys are
part of this source. Generic proposal detection is not identity verification;
unverified depth or liveness must never be described as secure biometrics.


## Reproduction and preview-coordinate checks

`make offline-tests` runs the 32 dependency-free lifecycle/layout tests. A C
compiler and Linux-PAM development headers are needed for `make all`. Inside an
isolated disposable Linux VM with no network, host mounts or hardware passthrough,
`make vm-tests` executes the 45 synthetic tests against real libpam. Run this as
both root and an ordinary UID; do not install the fixture modules into the
system authentication stack. No pretrained models or real password backend are
used. There is deliberately no install target.

The 13 additional coordinate and object-plane tests require NumPy and OpenCV.
From the repository root, use `PYTHONPATH=identity-research/src:identity-research/tests:replacement/userspace python3 -m unittest test_coordinate_profile test_planar_alignment`.
They contain only synthetic image/point fixtures. `sp7-research-ir-mirror-x-v1`
is a separate inactive profile; the preserved base image pipeline is unchanged.
Its filtered/normalized previews are unsuitable as absolute photometric PAD
measurements. See RESULTS.md for limits and the next actual-presence probe.

The companion workbench 0.4 remains intentionally pinned to the earlier camera
source commit 153d0e24b31c94de535ca9d06e9610d62ca06073. This follow-up is not
silently added to its already-tested archive and is not deployed to PAM or SP7.
