# SPDX-License-Identifier: GPL-3.0-only
"""Explicit SP7 research image coordinates; never an authentication decision.

The fixed central RGB window addresses proposal-detector input scale. It does
not establish RGB/IR geometric calibration or permit ignoring additional people.
White balance is provisional and must come from the selected capture profile.
"""
import math
import numpy as np

RGB_ROTATION_QUARTERS = 2
IR_ROTATION_QUARTERS = 1


def raw_plane(raw, shape):
    if not isinstance(raw, np.ndarray) or raw.dtype != np.dtype('uint16') or raw.shape != shape:
        raise ValueError('Unexpected unpacked sensor layout')
    if np.any(raw > 1023):
        raise ValueError('Unexpected raw sample range')
    return raw


def rgb_image(raw, gains, white, *, cv=None):
    if cv is None:
        import cv2 as cv
    raw_plane(raw, (1944, 2592))
    g = np.asarray(gains, dtype=np.float32)
    if g.shape != (3,) or not np.isfinite(g).all() or np.any(g < .25) or np.any(g > 4):
        raise ValueError('Invalid provisional color gains')
    if isinstance(white, bool) or not math.isfinite(white) or not 4 <= white <= 4092:
        raise ValueError('Invalid display white reference')
    x = cv.cvtColor(raw, cv.COLOR_BayerBGGR2RGB_EA).astype(np.float32)
    x = np.rot90(np.maximum(x - 16, 0), RGB_ROTATION_QUARTERS)
    x = np.clip(x * g / white, 0, 1)
    x = np.where(x <= .0031308, 12.92*x, 1.055*x**(1/2.4) - .055)
    return np.ascontiguousarray(np.rint(x * 255).astype(np.uint8))


def rgb_proposal_window(rgb):
    if not isinstance(rgb, np.ndarray) or rgb.dtype != np.uint8 or rgb.shape != (1944, 2592, 3):
        raise ValueError('Unexpected full RGB image')
    h, w = rgb.shape[:2]
    return np.ascontiguousarray(rgb[h//4:3*h//4, w//4:3*w//4]), (w//4, h//4)


def ir_image(raw, *, filtered=True, cv=None):
    if cv is None:
        import cv2 as cv
    raw_plane(raw, (480, 640))
    if type(filtered) is not bool:
        raise ValueError('Filter choice must be explicit')
    x = np.rot90(raw, IR_ROTATION_QUARTERS).astype(np.float32)
    if filtered:
        x = cv.bilateralFilter(x, 5, 2.5, 1.2)
    lo, hi = np.percentile(x, [1, 99]);hi = max(float(hi), float(lo) + 4)
    y = np.rint(np.clip((x-lo)/(hi-lo), 0, 1) * 255).astype(np.uint8)
    y = cv.createCLAHE(2.0, (8,8)).apply(y)
    return cv.cvtColor(y, cv.COLOR_GRAY2RGB)


def map_rgb_proposals(result, origin):
    """Retain original detector flags; report full oriented RGB coordinates."""
    if (not isinstance(origin, tuple) or origin != (648, 486) or
            result.get('authentication_allowed') is not False or
            result.get('password_required') is not True or result.get('PAD_verified') is not False):
        raise ValueError('Unverified proposal contract')
    faces=[]
    for f in result['faces']:
        b=f['box_xyxy']
        if len(b) != 4 or not all(math.isfinite(x) for x in b) or not (0 <= b[0] < b[2] <= 1296 and 0 <= b[1] < b[3] <= 972):
            raise ValueError('Invalid window coordinates')
        faces.append(dict(f,box_xyxy=[b[0]+648,b[1]+486,b[2]+648,b[3]+486]))
    return dict(result,faces=faces,coordinate_space='oriented_full_RGB',central_window_only=True,
                full_field_multiple_person_exclusion_verified=False,geometric_RGB_IR_calibration_verified=False)
