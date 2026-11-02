# Microsoft Surface Pro 7 Face ID research

Research into simultaneous front RGB/IR capture on Manjaro and an eventual
face-login system. Secure biometric authentication and PAD are not completed.

The [independent replacement source](replacement/README.md) implements a new
OV7251 lifecycle/readback layer on a licensed Linux baseline, a hash-bound
TensorFlow UINT8 proposal backend and tested recovery primitives. Inherited
uncertain-license OV7251 diagnostic/STROBE patches and Caffe FP16 weights are
excluded. This is an experimental source checkpoint with an inactive workbench installer, not a face-login release.

Kernel-derived code retains GPLv2 and upstream attribution. Standalone project
userspace retains GPLv3. No firmware, pretrained weights, private photographs,
embeddings, machine credentials or private conversations are included.

See [verification evidence](replacement/TEST-EVIDENCE.json) and the
[Manjaro companion](https://github.com/BogeBear/Microsoft-Surface-Pro-7-Manjaro).

## New capture verification and inactive package

Two new presence-authorized captures each delivered30RGB+30IR frames and
completed native/kernel/root shutdown, exact setting restoration and fresh
eight-device idle checks. Private raw files were hash/fsync-exported and
removed from device RAM. Only aggregate technical results are published.

The diagnostic UINT8 backend found one face proposal in14/14 brighter IR
frames per capture after spatial filtering, versus12/14 and13/14 unfiltered.
A fixed upright RGB central window gave29/30 and17/30; this remains too unstable
for an authentication claim. The window does not establish absence of other
people elsewhere. No threshold was lowered; no identity comparison, enrollment,
PAD or geometric RGB/IR calibration was performed. See replacement/PHYSICAL-EVIDENCE.json.

See the companion Manjaro draft for the source-only inactive workbench installer
and its install/upgrade/uninstall/rollback tests. Installing that package never
loads a driver or enables a camera, autostart, PAM or SDDM integration.

The [MIT interface and geometry prototype](interface/README.md) and
[bounded client-inventory follow-up](replacement/CLIENT-INVENTORY.md) are
included for review. New left/right captures verify RGB spatial coverage,
but IR detection away from centre remains unresolved; no login release is
claimed. All public documentation and prompts are English.

The separate [seven-module driver source kit](driver-build-kit/README.en.txt)
includes the reviewed INT3472/IPU4 source and independent OV7251. It preserves
GPLv2/MIT/UAPI notices, excludes inherited OV7251 diagnostic/STROBE derivatives
and contains no firmware or compiled modules. All seven modules build against
the exact target ABI. Fresh module identities differ from some recorded
runtime versions: building the kit is not authorization to replace them or
proof of physical validation of the fresh build. The inactive workbench omits
this development-host kernel source kit from its device payload.
