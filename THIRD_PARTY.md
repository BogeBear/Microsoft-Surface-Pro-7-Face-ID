# Component licensing and source scope

Standalone project userspace and installer sources are GPL-3.0-only unless
a component states otherwise. Linux/Intel-derived sensor, regulator and IPU4
source in replacement/drivers and driver-build-kit retains its GPLv2 terms,
original author notices and marked MIT/Linux-syscall-note exceptions. Root
GPLv3 does not relicense these components. Kernel-derived fault harnesses
retain GPLv2 alongside their source. Full license texts accompany each scope.

The interface and geometry subtree is MIT-licensed project code, retaining
Copyright(c)2026SP7 IR project contributors and full permission/warranty text.
The HAL-inspired eye is drawn in QML; no film assets, fonts or audio are
bundled. No rights to third-party names or trademarks are granted.

OpenCV, NumPy, Qt6 and GTK/PyGObject are external dependencies under their
own version/component terms. No runtime libraries, firmware, pretrained
weights, training images, private camera images or credentials are bundled.
The exact external UINT8 model/configuration and separate publisher terms
are identified in replacement/MODEL-PROVENANCE.json; no training-data rights
or biometric/PAD validity are inferred. There is no Caffe FP16 loader or
weight conversion fallback.

IPU4 and INT3472 provenance records identify reviewed upstream source and
documented changes. Older uncertain-license OV7251 additions and their
derived old tests/snapshots are excluded. The new sensor uses a licensed
Linux baseline plus newly written lifecycle/gate code. Prior exposure is
disclosed; no untouched clean-room or legal-certification claim is made.
Historical source snapshots and private research originals remain separate.

The source kit's753IPU4 files match the recorded runtime source in body:
740are byte-identical and13add approved modification notices/blank lines.
Fresh binaries are not claimed identical to recorded loaded modules. All
new runtime/module replacements require their own trust, version, cold-start,
idle and complete shutdown evidence. No authentication release is claimed.
