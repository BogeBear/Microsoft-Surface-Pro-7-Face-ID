# SPDX-License-Identifier: GPL-3.0-or-later
"""Object-only, provisional 2D registration. Never biometric calibration.

Normalized image coordinates permit explicit preview resolution changes. A
single plane cannot determine depth, camera intrinsics, stereo calibration,
physical timing, or whether the surface is living tissue.
"""
import cv2 as cv
import numpy as np


def gray(image):
    if type(image) is not np.ndarray or image.dtype!=np.uint8 or image.ndim not in (2,3):
        raise ValueError('expected uint8 preview')
    if image.ndim==3:
        if image.shape[2]!=3:raise ValueError('expected RGB')
        image=cv.cvtColor(image,cv.COLOR_RGB2GRAY)
    h,w=image.shape
    if min(h,w)<64 or max(h,w)>4096:raise ValueError('preview size budget')
    scale=min(1.,1280/max(h,w))
    if scale<1:image=cv.resize(image,(round(w*scale),round(h*scale)),interpolation=cv.INTER_AREA)
    return cv.createCLAHE(2.,(8,8)).apply(image)


def features(image):
    keys,desc=cv.SIFT_create(nfeatures=2500).detectAndCompute(image,None)
    if desc is None:return keys,None
    # RootSIFT is used only for an exploratory cross-spectrum object match.
    desc=np.sqrt(desc/np.maximum(desc.sum(axis=1,keepdims=True),1e-12))
    return keys,desc.astype(np.float32)


def pairs(a,b):
    if a is None or b is None or len(a)<2 or len(b)<2:return []
    matcher=cv.BFMatcher(cv.NORM_L2)
    def ratio(x,y):
        return {m.queryIdx:m.trainIdx for row in matcher.knnMatch(x,y,k=2)
                if len(row)==2 for m,n in [row] if m.distance<.7*n.distance}
    forward=ratio(a,b);back=ratio(b,a)
    return [(i,j) for i,j in forward.items() if back.get(j)==i]


def fit_points(source,target):
    s=np.asarray(source,dtype=np.float64);t=np.asarray(target,dtype=np.float64)
    if (s.shape!=t.shape or s.ndim!=2 or s.shape[1]!=2 or len(s)<12 or len(s)>2500 or
            not np.isfinite(s).all() or not np.isfinite(t).all() or
            (s<0).any() or (s>1).any() or (t<0).any() or (t>1).any()):
        raise ValueError('insufficient or invalid normalized correspondences')
    cv.setRNGSeed(524289)
    H,mask=cv.findHomography(s,t,cv.RANSAC,.006,maxIters=4000,confidence=.995)
    if H is None or mask is None:raise ValueError('no planar model')
    keep=mask.ravel().astype(bool)
    if keep.sum()<12 or keep.mean()<.3:raise ValueError('insufficient inliers')
    for p in (s[keep],t[keep]):
        if cv.contourArea(cv.convexHull(p.astype(np.float32)))<.02 or (np.ptp(p,axis=0)<.12).any():
            raise ValueError('correspondences too clustered')
    if not np.isfinite(H).all() or abs(np.linalg.det(H))<1e-12:raise ValueError('degenerate model')
    corners=np.array([[[0.,0.],[1.,0.],[1.,1.],[0.,1.]]])
    projected=cv.perspectiveTransform(corners,H)[0]
    if not np.isfinite(projected).all() or np.abs(projected).max()>10 or not cv.isContourConvex(projected.astype(np.float32)):
        raise ValueError('unstable extrapolation')
    q=cv.perspectiveTransform(s[None,:,:],H)[0]
    error=np.linalg.norm(q-t,axis=1)
    return dict(H=H.tolist(),inliers=int(keep.sum()),matches=len(s),
        inlier_fraction=float(keep.mean()),fitted_inlier_median_normalized_error=float(np.median(error[keep])),
        fitted_inlier_p95_normalized_error=float(np.percentile(error[keep],95)),
        error_is_in_sample_not_independent_validation=True,projected_unit_corners=projected.tolist(),
        biometric_calibration_verified=False,depth_verified=False,authentication_allowed=False)


def register(rgb,ir):
    r=gray(rgb);i=gray(ir);rk,rd=features(r);results=[]
    for mirror in (False,True):
        candidate=np.ascontiguousarray(i[:,::-1]) if mirror else i
        ik,idesc=features(candidate);matched=pairs(idesc,rd)
        row=dict(mirrored_IR_hypothesis=mirror,mutual_ratio_matches=len(matched),IR_keypoints=len(ik),RGB_keypoints=len(rk),accepted=False)
        try:
            if len(matched)<12:raise ValueError('insufficient mutual correspondences')
            s=np.array([ik[a].pt for a,b in matched])/np.array([candidate.shape[1]-1,candidate.shape[0]-1])
            t=np.array([rk[b].pt for a,b in matched])/np.array([r.shape[1]-1,r.shape[0]-1])
            model=fit_points(s,t)
            H=np.array(model['H'])
            if mirror:H=H@np.array([[-1.,0.,1.],[0.,1.,0.],[0.,0.,1.]])
            row.update(model,accepted=True,H_original_normalized_IR_to_normalized_RGB=H.tolist())
        except ValueError as e:row['reason']=str(e)
        results.append(row)
    return dict(candidates=results,RGB_processing_shape=list(r.shape),IR_processing_shape=list(i.shape),
        static_planar_object_only=True,authentication_allowed=False,depth_verified=False,
        geometric_calibration_verified=False,automatic_production_adoption=False)


def validate_fixed(rgb,ir,H_original,mirror):
    """Repeatability diagnostic on another static-object frame; never refits H."""
    if type(mirror) is not bool:raise ValueError('explicit mirror hypothesis required')
    H=np.asarray(H_original,dtype=float)
    if H.shape!=(3,3) or not np.isfinite(H).all():raise ValueError('invalid fixed model')
    r=gray(rgb);i=gray(ir);candidate=np.ascontiguousarray(i[:,::-1]) if mirror else i
    ik,idesc=features(candidate);rk,rd=features(r);matched=pairs(idesc,rd)
    if not matched:return dict(matches=0,within_fixed_threshold=0,model_refitted=False)
    s=np.array([ik[a].pt for a,b in matched])/np.array([candidate.shape[1]-1,candidate.shape[0]-1])
    if mirror:s[:,0]=1-s[:,0]
    t=np.array([rk[b].pt for a,b in matched])/np.array([r.shape[1]-1,r.shape[0]-1])
    q=cv.perspectiveTransform(s[None,:,:],H)[0];err=np.linalg.norm(q-t,axis=1);keep=err<=.006
    return dict(matches=len(matched),within_fixed_threshold=int(keep.sum()),
        all_matches_median_normalized_error=float(np.median(err)),
        supported_matches_median_normalized_error=float(np.median(err[keep])) if keep.any() else None,
        model_refitted=False,independent_scene_or_depth_validation=False)
