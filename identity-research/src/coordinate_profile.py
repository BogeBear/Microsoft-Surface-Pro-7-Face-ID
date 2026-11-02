# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit new preview/proposal profile. No physical capture or login hook."""
import numpy as np
from image_pipeline import ir_image

PROFILE_ID='sp7-research-ir-mirror-x-v1'
PHYSICAL_CALIBRATION_VERIFIED=False
PRODUCTION_ADOPTION=False


def ir_preview(raw, *, base=ir_image):
    """Rotate/filter via the preserved base, then mirror the full display plane.

    Box coordinates are in this new plane, not the legacy unmirrored plane.
    Callers must bind PROFILE_ID; a stored legacy box cannot be reused as-is.
    """
    image=base(raw,filtered=True)
    if not isinstance(image,np.ndarray) or image.dtype!=np.uint8 or image.shape!=(640,480,3):
        raise ValueError('unexpected oriented IR preview')
    return np.ascontiguousarray(image[:,::-1])


def legacy_box_to_profile(box):
    if (type(box) not in (list,tuple) or len(box)!=4 or
            any(type(x) not in (int,float) or not np.isfinite(x) for x in box) or
            not 0<=box[0]<box[2]<=480 or not 0<=box[1]<box[3]<=640):
        raise ValueError('invalid legacy oriented IR box')
    # Boxes use half-open extent coordinates; pixels use 479-x instead.
    return [480-box[2],box[1],480-box[0],box[3]]


def legacy_points_to_profile(points):
    """Subpixel centre coordinates use 479-x, unlike half-open box extents."""
    p=np.asarray(points,dtype=np.float64)
    if (p.ndim!=2 or p.shape[1]!=2 or not 1<=len(p)<=4096 or
            not np.isfinite(p).all() or (p<0).any() or
            (p[:,0]>479).any() or (p[:,1]>639).any()):
        raise ValueError('invalid legacy IR point coordinates')
    out=p.copy();out[:,0]=479-out[:,0]
    return out
