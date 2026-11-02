# Microsoft Surface Pro 7 Face ID research

Experimental simultaneous front RGB/IR capture on Manjaro, with an independent
sensor lifecycle and preparation for an eventual face-login system. **Secure
identity verification, PAD and production authentication are not implemented.**

## Source and licensing

The [replacement source](replacement/README.md) uses a licensed Linux OV7251
baseline with new lifecycle/readback control, a hash-bound TensorFlow UINT8
proposal interface, bounded capture and full shutdown/restoration contracts.
Uncertain-license inherited OV7251 diagnostic/STROBE derivatives and the former
FP16 dependency are excluded. Prior exposure to the old code is disclosed; no
clean-room or legal-certification claim is made.

Kernel-derived code retains GPLv2 and attribution. Standalone project code uses
GPLv3 under its file notices. The [interface and geometry prototype](interface/README.md)
retains MIT. No firmware, pretrained weights, compiled modules, photographs,
embeddings, credentials or private conversations are included.

## What is verified

Four separate actual-presence captures each delivered 30 RGB and 30 IR frames,
with native/kernel/light/root closure, exact restoration and fresh eight-device
idle checks. Private raw files were exported and removed from device RAM.
Only aggregate results are public.

The locked nine-window RGB proposal profile gives a single display group in
29/30 frames in each new left/right sequence. A separate static-object study
identified a horizontal-reflection mismatch between IR and RGB coordinates.
The [inactive coordinate candidate](identity-research/RESULTS.md), with unchanged
model, 0.8 threshold and full-frame scale, gives a single proposal in 14/14
brighter frames in all four sequences. The preserved baseline missed all 14
right-position frames. No proposals occur in the limited printed-object and
low-signal controls. These correlated sequences from one participant do not
establish identity accuracy, generalization, liveness, calibration or safety.
The new coordinate profile still needs fresh physical qualification.

The [identity research boundary](identity-research/README.md) adds a one-use
boot/account-bound attempt contract, an always-ignored diagnostic PAM module and
an offline configuration proposal. Real libpam VM tests verify password fallback
and required lockout/account checks. No real authentication configuration changes.

## Building and installing

The [source-only seven-module kit](driver-build-kit/README.en.txt) includes
reviewed INT3472/IPU4 and independent OV7251 code with GPLv2/MIT/UAPI notices.
All seven modules build for the exact target ABI. Some fresh IPU identities
differ from the physically tested runtime: a successful build is not permission
to silently replace controllers or evidence that those binaries work on hardware.

The [Manjaro companion](https://github.com/BogeBear/Microsoft-Surface-Pro-7-Manjaro)
provides an inactive workbench installer with tested install, upgrade, uninstall
and rollback. Version 0.4 intentionally stays pinned to source commit
153d0e24b31c94de535ca9d06e9610d62ca06073. This newer identity/coordinate follow-up
is not silently added to its tested archive. Installation never loads drivers,
starts cameras, enables autostart, or changes PAM/SDDM/boot/security policy.

See [capture evidence](replacement/PHYSICAL-EVIDENCE.json),
[test evidence](replacement/TEST-EVIDENCE.json),
[client-inventory follow-up](replacement/CLIENT-INVENTORY.md) and
[identity/coordinate verification](identity-research/VERIFICATION.json).
Uncertainty always requires password fallback. No login release is claimed.
