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
for the inactive workbench; all other reviewed interface files are unchanged.
