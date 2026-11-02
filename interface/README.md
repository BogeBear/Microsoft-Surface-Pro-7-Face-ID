# HAL-inspired interface and geometry research

This MIT-licensed project interface is retained from the already reviewed
2026-10-17 source snapshot. The eye is drawn in QML; no film images, audio,
external fonts or Qt artwork are bundled. Full MIT notices are retained at
interface/LICENSE and interface/ui/LICENSE. Project GPLv3 does not replace them.

Demo.qml is explicitly labelled a simulation. Its buttons neither authenticate
nor open a camera. Main.qml is a source SDDM password-frontend prototype:
it displays green only after the backend reports success for the pending
request, and binds the greeting to the submitted account name. There is no
biometric authentication backend or installer activation in this delivery.
The inactive workbench may preview Demo.qml as an ordinary user; it never
installs a theme or changes PAM/SDDM. No password or biometric data is logged.

The geometry library operates on supplied point correspondences and synthetic
calibration tests. No measured SP7 RGB/IR calibration is bundled, and generic
point reconstruction is not verified depth, liveness or presentation-attack
detection. Physical calibration and an independently validated biometric
backend remain separate work. The desktop-preview source path is adjusted
for the inactive workbench. Later UI changes are identified below and in PROVENANCE.json.


## Inactive research-attempt presentation

The 2026-11-02 follow-up adds `CameraResearchStatus.qml` and explicit Main.qml
hooks for a future trusted local controller. No controller, camera start or
privileged IPC is attached by default. The UI alone cannot claim presence,
clear a hardware hold, or authorize authentication.

Research progress keeps the eye red. A completed research result always leads
to the password prompt, including a synthetically eligible result. A missing,
late, wrong-account or wrong-attempt result cannot turn the eye green. The
eight-second presentation deadline moves to password fallback while retaining
an unknown-cleanup hold; it is not a replacement for the independent hardware
watchdog or verified closure. Password and research requests cannot overlap.

Green and the bound full-name/username greeting still require success from the
pending real password-backend request. The new layer never receives or stores
the password. All 41 QtTest passes (including fixture setup/cleanup) run locally
with Qt 6.11.2 offscreen and the software renderer. The first timeout-wiring test
found a presentation bug; an explicit fallback signal fixed it and the full
suite passes. No live SDDM, PAM, SP7 GUI or camera was changed.

The already-tested workbench 0.4 archive contains its earlier pinned interface,
not this newer source-only follow-up. Activation remains a separate future task.
