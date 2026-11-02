# Research results and next physical qualification

## Inactive identity automation

The real Linux-PAM VM run passes **45 tests as root and the same 45 as UID
1000**. This includes 22 attempt-lifecycle tests, 10 offline PAM-layout tests
and 13 libpam control-flow tests. Synthetic modules substitute all password,
lockout and account decisions. No production PAM file is invoked or changed.
The VM is off and its base image is unchanged. The separate earlier 32-test run
is preserved as history.

The proposed insertion is bound to eight read-only configuration snapshots.
Any changed file requires a new review, including an apparently harmless
whitespace change. The proposal is not an installer and explicitly disallows
activation. A source-level diagnostic module always ignores authentication;
there is no identity/PAD backend or success switch.

## IR coordinate diagnosis

The new object capture provides 19 mutual descriptor matches after horizontal
IR reflection, with 14 planar-model inliers. Without reflection there were zero
mutual matches. A fixed model checked on two other frame pairs supports 9/15 and
13/18 matches at the original normalized residual threshold without refitting.
The model visibly aligns the printed box plane. It does not align arbitrary
depth, establish stereo calibration, or verify physical timing. Fit residuals
are not independent calibration accuracy.

Using the reflected full IR plane and the unchanged detector/model/0.8 threshold:

| New capture | Brighter IR frames | Single proposal before | Single proposal after |
| --- | ---: | ---: | ---: |
| Centre 1 | 14 | 14 | 14 |
| Centre 2 | 14 | 14 | 14 |
| Left | 14 | 14 | 14 |
| Right | 14 | 0 | 14 |

No spatial tiling or threshold reduction is used. Separate controls yield zero
proposals on 14 brighter printed-object frames and 64 darker low-signal frames.
These are small, correlated sequences from one participant and one object, not
identity accuracy, generalization, spoof resistance or PAD validation.

The coordinate candidate has an explicit profile identifier. Existing raw
captures, base processing and old failed/negative reports are untouched.
Subpixel point centres use `479-x`; half-open box extents use `480-x`. No
legacy box, calibration or cached result can silently acquire the new binding.
This is an offline candidate, not a newly qualified physical profile.

Histogram normalization, bilateral filtering and CLAHE are display/proposal
processing. They destroy absolute radiometric relationships and must not be
reused as evidence of skin reflectance or liveness. Preserve raw samples and
exposure/gain/illumination metadata for any future photometric study.

## Next physical probe

After fresh boot/checkpoint/version/temperature/idle checks, take new separate
actual-presence captures at centre, left and right with the coordinate profile
locked before acquisition. Keep the existing driver, source model, proposal
threshold and full shutdown contract. No automatic retry and no reuse of old
Redo consent. Export privately before analysis on the development host.

Then acquire a visible, measured target at multiple positions/angles for actual
intrinsics, distortion and stereo validation, including independent holdouts.
The object-plane map is not transferable to a face-depth model. Physical exposure
clock conversion remains an independent requirement.

Enrollment, identity matching, negative participants and spoof/PAD evaluation,
bounded authenticated IPC, a real password-recovery drill and rollback are still
needed before an authentication path may be enabled. All present paths fall
back to a password. No camera has been started while the user is away.
