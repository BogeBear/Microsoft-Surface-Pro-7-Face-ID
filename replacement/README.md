# Independent replacement source checkpoint

This source checkpoint replaces the inherited OV7251 additions with a newly
written lifecycle layer on the licensed linux-surface sensor baseline. Prior
exposure to the older implementation is disclosed; this is not represented as
an untouched clean-room process or a legal certification. Existing Linux
notices and GPLv2 obligations remain. See drivers/ov7251/PROVENANCE.json.

The UINT8 detector verifies exact model/configuration bytes before OpenCV loads
them. There is no Caffe FP16 loader, converter, download or fallback. Trained
weights remain external; MODEL-PROVENANCE.json identifies the separately
reviewed publisher terms. Detection scores are not identity probabilities.

## Delivered components

- drivers/ov7251: GPLv2 Linux sensor derivative and new gate/lifecycle core.
  The original four mode/global register arrays are retained unchanged.
- userspace: GPLv3 status/model validation, in-stream gate readbacks, RAM staging
  and injected-I/O recovery contracts. They have no unattended camera launcher,
  privilege grant, PAM entry or authentication-enablement path.
- native/camera-state.c: GPLv3 format/crop snapshot primitive. ENOTTY on a
  read-only crop requires a fresh exact crop readback; other errors still fail.
- tests: GPLv2 C lifecycle tests and GPLv3 userspace/native-fixture tests.

## Building and offline checks

The module requires matching7.2.11-arch1-1-surface development headers:

```sh
make -C replacement/drivers/ov7251 KDIR=/path/to/matching/kernel/build
sh replacement/run-offline-tests.sh
```

The offline script needs a C compiler, Python3 and NumPy, and refuses root.
Root staging tests deliberately skip there. They were separately run as root
inside an isolated disposable VM without a NIC, host mounts or passthrough;
never run privileged tests against a workstation root filesystem.
Actual model inference additionally requires OpenCV and the exact external
model files. No dependencies are automatically installed or downloaded.

## Hardware and release boundary

The module's experimental_hardware parameter defaults to0, refusing sensor
probing. Opt-in also requires an exact Microsoft Surface Pro7 DMI match.
There is no automatic module installation or boot activation. The operational camera controller and persistent driver installation are still
being migrated. The separate inactive workbench installer is VM-verified;
it installs source only and does not activate hardware or authentication.

The writer ir_control accepts only capture and off. ir_snapshot returns a
fixed raw register list. ir_strobe_test is a read-only compatibility view for
the full idle reader; the old writable API is not restored. New controllers
must bind the actual module version and the complete current API together.

Only gate-enable bits are controlled: output direction3005:3, frame trigger
3b80:4 and STROBE source enable3b96:7. Frequency, duty, current, frame pattern,
shift, span and pulse settings are not tuned. All other bits must match fresh
readbacks. The requested software deadline is3seconds; workqueue scheduling
is not a hardware cutoff or a hard real-time guarantee. Register readbacks
alone do not prove optical output or exact exposure synchronization.

Runtime control changes during prepared/active streaming are refused. Exposure
can be selected before a stream; its current value is distinct from its stable
control default. Continuous auto-exposure and suspend/resume are not validated.

Unknown client visibility, temperature, light closure, native unmap/release,
kernel stop/close, root exit or configuration restoration must remain failure.
A status string is never a complete eight-device idle receipt. Recovery graph
comparison may ignore only entity IDs/listing order and ID-width-dependent
indentation; capture transactions still require their own exact original graph.

No enrollment, PAM/SDDM integration, identity security,3D reconstruction or PAD
is enabled or claimed. Password fallback remains required.

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
PAD or geometric RGB/IR calibration was performed. See PHYSICAL-EVIDENCE.json.

See the companion Manjaro draft for the source-only inactive workbench installer
and its install/upgrade/uninstall/rollback tests. Installing that package never
loads a driver or enables a camera, autostart, PAM or SDDM integration.

## Next spatial proposal candidate

The optional `userspace/spatial_proposals.py` checks nine fixed overlapping
half-size RGB windows, including corners, edge middles and centre. Errors
in any view stop the result; a bounded candidate budget prevents unbounded
display grouping. The same unchanged0.8 model threshold gives29/30 and25/30
single display groups on the two new captures, versus29/30 and17/30 for the
central window alone. This is exploratory reuse of those two captures, not
a held-out physical test. Seven synthetic coverage/error/budget tests pass.

Overlap grouping is only a display convenience. It does not identify people
or prove absence of other people. Authentication remains disabled and
password login remains required. New positions and fresh captures, plus
actual device runtime validation, are needed before relying on this candidate.

## Locked-profile new positions and inventory recovery

Two additional fresh captures with explicit left/right dialog instructions
passed30RGB+30IR each and complete independent teardown/restoration checks.
The fixed RGB nine-window candidate gave29/30 in both new sequences; the
central window alone gave15/30 and0/30. This is a useful coverage improvement,
not population accuracy or biometric verification. Filtered full-frame IR gave
14/14 on the left and0/14 on the right despite visible facial detail. A later
IR tiling experiment produced additional off-face proposals and is rejected
as the default. Do not hide ambiguity or promote proposal scores to identity.

The compositor-fd preflight failure was preserved. No camera/configuration
started in that failed trial. The typed bounded reader fix then completed
two actual capture cycles. See CLIENT-INVENTORY.md. The public reader has
example host bindings and is not a ready privileged installation. The public
presence/dialog counterpart is English; the private SP7 test prompts are
localized. Real one-use presence and full shutdown contracts are unchanged.

The MIT-licensed interface/geometry source is included at ../interface with
its original notices. Its demo is a visual simulation, not authentication.
Physical RGB-to-IR calibration and production controller/driver installation
remain unfinished. Password login remains required.
