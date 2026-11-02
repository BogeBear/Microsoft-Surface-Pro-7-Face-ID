"""Offline RGB/IR geometry. No camera, identity matching or authorization.

Convention: X_rgb = R @ X_ir + t, in metres; x right, y down, z forward.
Only corresponding, undistorted-via-OpenCV image points may be triangulated.
"""
from dataclasses import dataclass
import hashlib
import json
import math

import cv2
import numpy as np


def finite(value, shape=None):
    a = np.asarray(value, dtype=np.float64)
    if (shape is not None and a.shape != shape) or not np.isfinite(a).all():
        raise ValueError('Invalid shape or nonfinite geometry')
    return a


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def camera(value):
    for key in ('device_id', 'mode_id', 'pixel_transform_id'):
        if not isinstance(value.get(key), str) or not value[key]:
            raise ValueError('Missing camera/mode/pixel-transform binding')
    size = value.get('size')
    if (not isinstance(size, list) or len(size) != 2 or
            any(type(n) is not int or n <= 0 for n in size)):
        raise ValueError('Invalid camera dimensions')
    k = finite(value['K'], (3, 3))
    d = finite(value['distortion'])
    if d.ndim != 1 or d.size not in (4, 5, 8, 12, 14):
        raise ValueError('Unsupported distortion model')
    if (k[0, 0] <= 0 or k[1, 1] <= 0 or
            not np.allclose(k[2], [0, 0, 1]) or k[0, 1] != 0 or k[1, 0] != 0 or
            not 0 <= k[0, 2] < size[0] or not 0 <= k[1, 2] < size[1]):
        raise ValueError('Invalid pinhole intrinsics')
    return k, d


def validate_calibration(c):
    if c.get('schema') != 'sp7-stereo-v1' or c.get('units') != 'metres':
        raise ValueError('Unknown calibration schema/units')
    if c.get('source') not in ('synthetic', 'measured-target') or not c.get('target_id'):
        raise ValueError('Unknown calibration source or target')
    camera(c['ir']); camera(c['rgb'])
    if c['ir']['device_id'] == c['rgb']['device_id']:
        raise ValueError('Two distinct cameras required')
    r = finite(c['R_rgb_from_ir'], (3, 3)); t = finite(c['t_rgb_from_ir_m'], (3,))
    if not np.allclose(r.T @ r, np.eye(3), atol=1e-6) or not math.isclose(np.linalg.det(r), 1, abs_tol=1e-6):
        raise ValueError('Improper rotation')
    if not 1e-5 <= np.linalg.norm(t) <= 1:
        raise ValueError('Missing or implausible baseline')
    return r, t


@dataclass(frozen=True)
class Frame:
    """Exposure midpoint in a shared monotonic clock, not application arrival time."""
    device_id: str
    mode_id: str
    pixel_transform_id: str
    size: tuple
    capture_id: str
    clock_id: str
    timestamp_ns: int
    uncertainty_ns: int


def check_pair(c, ir, rgb, max_skew_ns):
    validate_calibration(c)
    if type(max_skew_ns) is not int or not 0 < max_skew_ns <= 100_000_000:
        raise ValueError('Explicit finite pairing tolerance required')
    for f, key in ((ir, 'ir'), (rgb, 'rgb')):
        binding = c[key]
        if any(getattr(f, field) != binding[field] for field in ('device_id', 'mode_id', 'pixel_transform_id')):
            raise ValueError('Frame not bound to calibrated camera mode/transform')
        if tuple(binding['size']) != tuple(f.size):
            raise ValueError('Frame resolution changed')
        if (type(f.timestamp_ns) is not int or f.timestamp_ns < 0 or
                type(f.uncertainty_ns) is not int or f.uncertainty_ns < 0):
            raise ValueError('Unknown or invalid exposure time')
    if (not ir.capture_id or ir.capture_id != rgb.capture_id or
            not ir.clock_id or ir.clock_id != rgb.clock_id):
        raise ValueError('Unrelated capture or clock domains')
    bound = abs(ir.timestamp_ns-rgb.timestamp_ns)+ir.uncertainty_ns+rgb.uncertainty_ns
    if bound > max_skew_ns:
        raise ValueError('Exposure intervals too far apart or uncertain')
    return bound


def image_points(points, size):
    p = finite(points)
    if p.ndim != 2 or p.shape[1] != 2 or not 1 <= len(p) <= 4096:
        raise ValueError('Expected bounded Nx2 image correspondences')
    if (p < 0).any() or (p >= np.asarray(size)).any():
        raise ValueError('Image point out of bounds')
    return p


def triangulate(c, ir_frame, rgb_frame, ir_points, rgb_points, *, max_skew_ns,
                max_reprojection_px=1.5, min_angle_deg=0.25, depth_range_m=(0.15, 1.5)):
    """Sparse metric geometry, with positive-depth, ray-angle and residual checks.

    Point correspondence has to be established independently. Small residuals
    do not prove semantic matches, a live face, or calibrated biometric safety.
    """
    skew = check_pair(c, ir_frame, rgb_frame, max_skew_ns)
    r, t = validate_calibration(c)
    thresholds = finite([max_reprojection_px, min_angle_deg, *depth_range_m], (4,))
    if not (thresholds[0] > 0 and 0 < thresholds[1] < 90 and 0 < thresholds[2] < thresholds[3]):
        raise ValueError('Invalid diagnostic bounds')
    a = image_points(ir_points, c['ir']['size']); b = image_points(rgb_points, c['rgb']['size'])
    if a.shape != b.shape:
        raise ValueError('Unpaired image points')
    k1, d1 = camera(c['ir']); k2, d2 = camera(c['rgb'])
    u1 = cv2.undistortPoints(a.reshape(-1, 1, 2), k1, d1).reshape(-1, 2)
    u2 = cv2.undistortPoints(b.reshape(-1, 1, 2), k2, d2).reshape(-1, 2)
    h = cv2.triangulatePoints(np.column_stack((np.eye(3), np.zeros(3))),
                             np.column_stack((r, t)), u1.T, u2.T)
    rows = []
    for i in range(len(a)):
        row = {'index': i, 'valid': False, 'point_ir_m': None, 'reason': 'degenerate'}
        if not np.isfinite(h[:, i]).all() or abs(h[3, i]) < 1e-12:
            rows.append(row); continue
        p = h[:3, i]/h[3, i]; q = r @ p+t
        if p[2] <= 0 or q[2] <= 0:
            row['reason'] = 'behind-camera'; rows.append(row); continue
        v1 = np.r_[u1[i], 1.]; v2 = r.T @ np.r_[u2[i], 1.]
        angle = float(np.degrees(np.arccos(np.clip(v1 @ v2 / np.linalg.norm(v1) / np.linalg.norm(v2), -1., 1.))))
        projected1 = cv2.projectPoints(p.reshape(1, 3), np.zeros(3), np.zeros(3), k1, d1)[0].reshape(2)
        projected2 = cv2.projectPoints(p.reshape(1, 3), cv2.Rodrigues(r)[0], t, k2, d2)[0].reshape(2)
        error = max(float(np.linalg.norm(projected1-a[i])), float(np.linalg.norm(projected2-b[i])))
        row.update(ray_angle_deg=angle, reprojection_error_px=error)
        if not depth_range_m[0] <= p[2] <= depth_range_m[1]: row['reason'] = 'depth-range'
        elif angle < min_angle_deg: row['reason'] = 'weak-parallax'
        elif error > max_reprojection_px: row['reason'] = 'reprojection'
        else: row.update(valid=True, point_ir_m=p.tolist(), reason='geometry-only')
        rows.append(row)
    return {'schema': 'sp7-geometry-result-v1', 'calibration_sha256': digest(c),
            'source': c['source'], 'exposure_skew_bound_ns': skew, 'points': rows,
            'valid_points': sum(x['valid'] for x in rows),
            'authentication_granted': False, 'liveness_verified': False,
            'scope': 'Offline sparse geometry, not identity, liveness or authentication'}


def calibrate(ir_spec, rgb_spec, object_views_m, ir_views, rgb_views, *, target_id, source):
    """Fit intrinsics and relative pose from corresponding known target corners.

    Calibration-set RMS is diagnostic only; independent holdout measurements,
    target scale verification and cross-spectrum visibility are still required.
    """
    n = len(object_views_m)
    if not 8 <= n <= 200 or len(ir_views) != n or len(rgb_views) != n:
        raise ValueError('Need 8..200 corresponding target views')
    if source not in ('synthetic', 'measured-target') or not target_id:
        raise ValueError('Explicit target and source required')
    objects, left, right = [], [], []
    for obj, a, b in zip(object_views_m, ir_views, rgb_views):
        o = finite(obj)
        a = image_points(a, ir_spec['size']); b = image_points(b, rgb_spec['size'])
        if o.shape != (len(a), 3) or len(a) != len(b) or len(a) < 12:
            raise ValueError('Invalid target correspondences')
        objects.append(o.astype(np.float32)); left.append(a.astype(np.float32)); right.append(b.astype(np.float32))
    rms1, k1, d1, _, _ = cv2.calibrateCamera(objects, left, tuple(ir_spec['size']), None, None)
    rms2, k2, d2, _, _ = cv2.calibrateCamera(objects, right, tuple(rgb_spec['size']), None, None)
    # With FIX_INTRINSIC, imageSize does not rescale either separately fitted K.
    rms, _, _, _, _, r, t, _, _ = cv2.stereoCalibrate(objects, left, right, k1, d1, k2, d2,
                tuple(ir_spec['size']), flags=cv2.CALIB_FIX_INTRINSIC,
                criteria=(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-9))
    result = {'schema': 'sp7-stereo-v1', 'units': 'metres', 'source': source, 'target_id': target_id,
              'ir': {**ir_spec, 'K': k1.tolist(), 'distortion': d1.ravel().tolist()},
              'rgb': {**rgb_spec, 'K': k2.tolist(), 'distortion': d2.ravel().tolist()},
              'R_rgb_from_ir': r.tolist(), 't_rgb_from_ir_m': t.ravel().tolist(),
              'fit': {'views': n, 'ir_rms_px': rms1, 'rgb_rms_px': rms2, 'stereo_rms_px': rms,
                      'independent_validation': False}, 'biometric_validation': False}
    validate_calibration(result)
    return result


def register_ir_to_rgb(c, ir_frame, rgb_frame, ir_image, depth_m, *, max_skew_ns):
    """Project IR samples using supplied metric depth, with nearest-depth z-buffer.

    Zero/NaN depth stays unknown. Does not infer depth from IR brightness,
    enlarge sparse points, fill holes, blend modalities, or authorize anything.
    Return values are radiometrically unchanged float samples and a valid mask.
    """
    check_pair(c, ir_frame, rgb_frame, max_skew_ns)
    r, t = validate_calibration(c)
    image = np.asarray(ir_image)
    depth = np.asarray(depth_m, dtype=float)
    expected = tuple(reversed(c['ir']['size']))
    if image.shape != expected or depth.shape != expected or image.size > 16_000_000:
        raise ValueError('IR/depth dimensions do not match calibrated mode')
    if image.dtype.kind not in 'uif' or not np.isfinite(image).all():
        raise ValueError('Invalid IR intensity data')
    if np.isinf(depth).any() or (depth[np.isfinite(depth)] < 0).any():
        raise ValueError('Invalid depth data')
    ys, xs = np.nonzero(np.isfinite(depth) & (depth > 0))
    k1, d1 = camera(c['ir']); k2, d2 = camera(c['rgb'])
    h, w = reversed(c['rgb']['size'])
    registered = np.full((h,w), np.nan, dtype=np.float32)
    valid = np.zeros((h,w), dtype=bool)
    if not len(xs): return registered, valid
    rays = cv2.undistortPoints(np.column_stack((xs,ys)).astype(float).reshape(-1,1,2),k1,d1).reshape(-1,2)
    xyz = np.column_stack((rays, np.ones(len(xs)))) * depth[ys,xs,None]
    rgb_xyz = xyz @ r.T+t
    uv = cv2.projectPoints(xyz, cv2.Rodrigues(r)[0],t,k2,d2)[0].reshape(-1,2)
    keep = (rgb_xyz[:,2]>0) & np.isfinite(uv).all(axis=1)
    keep &= (uv[:,0]>=0) & (uv[:,0]<w-.5) & (uv[:,1]>=0) & (uv[:,1]<h-.5)
    indices = np.flatnonzero(keep)
    if not len(indices): return registered, valid
    px = np.rint(uv[indices]).astype(int)
    order = np.argsort(rgb_xyz[indices,2], kind='stable')
    pixel_ids = px[order,1]*w+px[order,0]
    _, first = np.unique(pixel_ids, return_index=True)
    chosen = indices[order[first]]; target = px[order[first]]
    registered[target[:,1],target[:,0]] = image[ys[chosen],xs[chosen]]
    valid[target[:,1],target[:,0]] = True
    return registered, valid
