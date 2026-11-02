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
There is no automatic module installation or boot activation. The operational
controller and installation/upgrade/uninstall/rollback package are still being
migrated and are not a completed release in this checkpoint.

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
