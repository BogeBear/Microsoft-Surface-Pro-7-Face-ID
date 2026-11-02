# SPDX-License-Identifier: GPL-3.0-only
"""Fixed RGB scale/coverage diagnostics, never identity or authentication.

All nine half-size windows are always checked, including off-centre windows.
Overlapping proposals are grouped only for display. Grouping is not evidence
that two crops describe the same identity or that nobody else is present.
"""
import math
import numpy as np


def overlap(a,b):
    w=max(0,min(a[2],b[2])-max(a[0],b[0]));h=max(0,min(a[3],b[3])-max(a[1],b[1]));inter=w*h
    return inter/((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter)


def collect(rgb,detector):
    if not isinstance(rgb,np.ndarray) or rgb.dtype!=np.uint8 or rgb.shape!=(1944,2592,3):
        raise ValueError('Unexpected oriented RGB plane')
    h,w=rgb.shape[:2];hh,ww=h//2,w//2
    views=[(0,0),(ww,0),(0,hh),(ww,hh),(w//4,h//4),
           (w//4,0),(w//4,hh),(0,h//4),(ww,h//4)]
    candidates=[];counts=[]
    for view,(x,y) in enumerate(views):
        result=detector.detect(np.ascontiguousarray(rgb[y:y+hh,x:x+ww]))
        if result.get('authentication_allowed') is not False or result.get('password_required') is not True or result.get('PAD_verified') is not False:
            raise ValueError('Unexpected detector decision contract')
        if len(result['faces'])>1000:raise ValueError('Proposal count limit')
        counts.append(len(result['faces']))
        for f in result['faces']:
            b=f['box_xyxy'];score=f['score']
            if len(b)!=4 or not all(math.isfinite(v) for v in b) or not(0<=b[0]<b[2]<=ww and 0<=b[1]<b[3]<=hh) or not math.isfinite(score) or not 0<=score<=1:
                raise ValueError('Invalid local proposal')
            candidates.append(dict(box_xyxy=[b[0]+x,b[1]+y,b[2]+x,b[3]+y],score=score,view=view))
            if len(candidates)>64:raise ValueError('Total spatial proposal budget exceeded')
    groups=[]
    for f in sorted(candidates,key=lambda f:f['score'],reverse=True):
        matched=[g for g in groups if overlap(g['box_xyxy'],f['box_xyxy'])>.3]
        if matched:matched[0]['supporting_views'].append(f['view'])
        else:groups.append(dict(box_xyxy=f['box_xyxy'],score=f['score'],supporting_views=[f['view']]))
    return dict(groups=groups,view_proposal_counts=counts,views_checked=9,all_windows_complete=True,
                raw_candidate_count=len(candidates),grouping_is_identity_matching=False,
                single_display_group=len(groups)==1,ambiguous_display_groups=len(groups)>1,
                full_field_multiple_person_exclusion_verified=False,
                authentication_allowed=False,password_required=True,PAD_verified=False)
