EXPERIMENTAL SP7 CURRENT CAMERA DRIVER SOURCE KIT

This standalone component builds seven modules against exact Surface kernel
7.2.11-arch1-1-surface headers. Build as an ordinary user:
  make -j4 KDIR=/path/to/matching/kernel/build
There is no installation, signing, module-loading, firmware-download, PAM,
SDDM or boot-change target. Keep large builds on the development host.
The inactive workbench installer omits this separate kernel build kit.

INT3472 and Intel IPU4 retain their reviewed GPLv2 source lineage and original
notices, with marked MIT/UAPI exceptions intact. The OV7251 directory contains
the new licensed-baseline lifecycle/gate implementation; inherited uncertain
diagnostic/STROBE additions and their old tests are excluded. Prior exposure
is disclosed: no untouched clean-room or legal-certification claim is made.

References in in-file modification notices are relative to this standalone
kit's root. The retained IPU4 dated-record and source-patch files accompany
them. DRIVER-PROVENANCE covers only INT3472; IPU4-PROVENANCE and
drivers/ov7251/PROVENANCE describe the other distinct lineages. Dates identify
documented records or notice additions, not invented first-edit timestamps.

SOURCE-COMPARISON records753 IPU4 files:740 byte-identical to the recorded
runtime source and13 differing only in approved modification notices/blank
lines. Seven fresh modules built with exact vermagic. Fresh module source
versions are not all identical to the recorded loaded versions; no silent
controller rebind, byte-identical claim or physical validation of the new
build is inferred. See BUILD-VERIFICATION. The physical tests used the
explicitly recorded runtime plus the new OV7251 module, not these fresh
IPU4 binaries. Revalidate trust, dependencies, versions, idle, cold-start and
complete STOP/CLOSE contracts before any proposed live replacement.

No compiled modules, firmware, model weights, private images, credentials
or private conversations are part of this source inventory. Kernel-derived
source remains GPLv2; the userspace GPLv3 default does not relicense it.
