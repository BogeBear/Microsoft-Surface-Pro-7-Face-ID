import copy
import unittest

import cv2
import numpy as np

from stereo import Frame, calibrate, digest, register_ir_to_rgb, triangulate, validate_calibration


def fixture():
    def cam(device, size, k):
        return {'device_id': device, 'mode_id': 'synthetic-mode', 'pixel_transform_id': 'unmirrored-uncropped',
                'size': size, 'K': k, 'distortion': [-.03, .002, .0002, -.0001, 0.]}
    return {'schema': 'sp7-stereo-v1', 'units': 'metres', 'source': 'synthetic', 'target_id': 'synthetic-target-20mm',
            'ir': cam('synthetic-ir', [640, 480], [[520, 0, 320], [0, 515, 240], [0, 0, 1]]),
            'rgb': cam('synthetic-rgb', [1280, 960], [[1100, 0, 640], [0, 1095, 480], [0, 0, 1]]),
            'R_rgb_from_ir': cv2.Rodrigues(np.array([.002, -.009, .001]))[0].tolist(),
            't_rgb_from_ir_m': [-.03, .001, .0005]}


def frame(c, key, **kw):
    v=c[key]; args=dict(device_id=v['device_id'], mode_id=v['mode_id'], pixel_transform_id=v['pixel_transform_id'],
        size=tuple(v['size']), capture_id='synthetic-session', clock_id='synthetic-monotonic-boot', timestamp_ns=1_000_000_000, uncertainty_ns=100_000)
    args.update(kw); return Frame(**args)


def project(c, xyz):
    out=[]
    for key, r, t in [('ir',np.zeros(3),np.zeros(3)), ('rgb',cv2.Rodrigues(np.array(c['R_rgb_from_ir']))[0],np.array(c['t_rgb_from_ir_m']))]:
        out.append(cv2.projectPoints(xyz,r,t,np.array(c[key]['K'],dtype=float),np.array(c[key]['distortion']))[0].reshape(-1,2))
    return out


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.c=fixture(); self.xyz=np.array([[-.04,-.02,.45], [.02,.01,.6], [0.,-.01,.8]])
        self.a,self.b=project(self.c,self.xyz)

    def run_geometry(self, **kw):
        params=dict(c=self.c, ir_frame=frame(self.c,'ir'), rgb_frame=frame(self.c,'rgb'),
                    ir_points=self.a, rgb_points=self.b, max_skew_ns=2_000_000)
        params.update(kw); return triangulate(**params)

    def test_metric_reconstruction_with_distortion_and_unequal_resolution(self):
        d=self.run_geometry(); self.assertEqual(d['valid_points'],3)
        np.testing.assert_allclose([p['point_ir_m'] for p in d['points']],self.xyz,atol=1e-7)
        self.assertFalse(d['authentication_granted']); self.assertFalse(d['liveness_verified'])

    def test_mode_change_rejected(self):
        with self.assertRaises(ValueError): self.run_geometry(rgb_frame=frame(self.c,'rgb',mode_id='changed'))
    def test_crop_change_rejected(self):
        with self.assertRaises(ValueError): self.run_geometry(ir_frame=frame(self.c,'ir',pixel_transform_id='cropped'))
    def test_resolution_change_rejected(self):
        with self.assertRaises(ValueError): self.run_geometry(ir_frame=frame(self.c,'ir',size=(320,240)))
    def test_clock_domains_rejected(self):
        with self.assertRaises(ValueError): self.run_geometry(rgb_frame=frame(self.c,'rgb',clock_id='other-boot'))
    def test_unrelated_capture_rejected(self):
        with self.assertRaises(ValueError): self.run_geometry(rgb_frame=frame(self.c,'rgb',capture_id='other-session'))
    def test_time_skew_rejected(self):
        with self.assertRaises(ValueError): self.run_geometry(rgb_frame=frame(self.c,'rgb',timestamp_ns=1_004_000_000))
    def test_time_uncertainty_counts(self):
        with self.assertRaises(ValueError): self.run_geometry(rgb_frame=frame(self.c,'rgb',uncertainty_ns=3_000_000))
    def test_unknown_timestamp_rejected(self):
        with self.assertRaises(ValueError): self.run_geometry(rgb_frame=frame(self.c,'rgb',timestamp_ns=None))
    def test_nan_rejected(self):
        a=self.a.copy(); a[0,0]=np.nan
        with self.assertRaises(ValueError): self.run_geometry(ir_points=a)
    def test_mismatched_count_rejected(self):
        with self.assertRaises(ValueError): self.run_geometry(rgb_points=self.b[:2])
    def test_outside_image_rejected(self):
        a=self.a.copy(); a[0,0]=-1
        with self.assertRaises(ValueError): self.run_geometry(ir_points=a)
    def test_zero_baseline_rejected(self):
        self.c['t_rgb_from_ir_m']=[0,0,0]
        with self.assertRaises(ValueError): self.run_geometry()
    def test_reflection_rejected(self):
        self.c['R_rgb_from_ir']=np.diag([-1,1,1]).tolist()
        with self.assertRaises(ValueError): self.run_geometry()
    def test_unit_error_rejected(self):
        self.c['units']='millimetres'
        with self.assertRaises(ValueError): self.run_geometry()
    def test_weak_parallax_rejected(self):
        d=self.run_geometry(min_angle_deg=15); self.assertEqual(d['valid_points'],0)
    def test_mismatched_points_fail_residual_check(self):
        b=self.b.copy(); b[:,1]+=20
        d=self.run_geometry(rgb_points=b); self.assertEqual(d['valid_points'],0)
    def test_behind_camera_rejected(self):
        a,b=project(self.c,-self.xyz)
        self.assertEqual(self.run_geometry(ir_points=a,rgb_points=b)['valid_points'],0)
    def test_depth_bounds_rejected(self):
        self.assertEqual(self.run_geometry(depth_range_m=(.9,1.5))['valid_points'],0)
    def test_hash_changes_on_camera_parameter_change(self):
        before=digest(self.c); self.c['ir']['K'][0][0]+=1; self.assertNotEqual(before,digest(self.c))
    def test_invalid_limits_rejected(self):
        with self.assertRaises(ValueError): self.run_geometry(max_reprojection_px=float('nan'))
    def test_missing_calibration_source_rejected(self):
        self.c['source']='assumed'
        with self.assertRaises(ValueError): self.run_geometry()

    def test_fit_actual_opencv_calibration_and_independent_pose(self):
        board=np.zeros((54,3),np.float64); board[:,:2]=np.mgrid[0:9,0:6].T.reshape(-1,2)*.02
        board[:,:2]-=[.08,.05]
        objects=[]; left=[]; right=[]
        for i in range(14):
            rv=np.array([-.3+.05*i, .2*np.sin(i), .07*np.cos(i)])
            pose=board @ cv2.Rodrigues(rv)[0].T+np.array([.035*np.sin(i),.025*np.cos(i),.45+.013*i])
            a,b=project(self.c,pose); objects.append(board); left.append(a); right.append(b)
        specs=[{k:v for k,v in self.c[key].items() if k not in ('K','distortion')} for key in ('ir','rgb')]
        fitted=calibrate(*specs,objects,left,right,target_id='synthetic-target',source='synthetic')
        np.testing.assert_allclose(fitted['t_rgb_from_ir_m'],self.c['t_rgb_from_ir_m'],atol=1e-5)
        # The held-out three-depth points were not in the calibration board views.
        d=self.run_geometry(c=fitted)
        self.assertEqual(d['valid_points'],3)
        np.testing.assert_allclose([p['point_ir_m'] for p in d['points']],self.xyz,atol=2e-5)
        self.assertFalse(fitted['fit']['independent_validation'])
    def test_too_few_calibration_views_rejected(self):
        with self.assertRaises(ValueError): calibrate(self.c['ir'],self.c['rgb'],[],[],[],target_id='x',source='synthetic')

    def test_registration_uses_measured_depth_and_preserves_intensity(self):
        ir=np.zeros((480,640),dtype=np.uint16); ir[220,300]=777
        depth=np.zeros_like(ir,dtype=float); depth[220,300]=.6
        aligned,mask=register_ir_to_rgb(self.c,frame(self.c,'ir'),frame(self.c,'rgb'),ir,depth,max_skew_ns=2_000_000)
        self.assertEqual(mask.sum(),1); self.assertEqual(aligned[mask][0],777)
        self.assertTrue(np.isnan(aligned[~mask]).all())
    def test_no_depth_does_not_create_registration(self):
        ir=np.full((480,640),1023,dtype=np.uint16); depth=np.full(ir.shape,np.nan)
        aligned,mask=register_ir_to_rgb(self.c,frame(self.c,'ir'),frame(self.c,'rgb'),ir,depth,max_skew_ns=2_000_000)
        self.assertFalse(mask.any()); self.assertTrue(np.isnan(aligned).all())
    def test_registration_wrong_size_rejected(self):
        with self.assertRaises(ValueError): register_ir_to_rgb(self.c,frame(self.c,'ir'),frame(self.c,'rgb'),np.zeros((240,320)),np.zeros((240,320)),max_skew_ns=2_000_000)
    def test_registration_rejects_negative_depth(self):
        depth=np.full((480,640),-1.)
        with self.assertRaises(ValueError): register_ir_to_rgb(self.c,frame(self.c,'ir'),frame(self.c,'rgb'),np.zeros_like(depth),depth,max_skew_ns=2_000_000)
    def test_registration_occlusion_nearest_sample_wins(self):
        c=copy.deepcopy(self.c); c['R_rgb_from_ir']=np.eye(3).tolist(); c['t_rgb_from_ir_m']=[-.03,0,0]
        for key in ('ir','rgb'):
            c[key]['K']=[[100.,0,320],[0,100.,240],[0,0,1]]; c[key]['distortion']=[0.,0,0,0,0]
        ir=np.zeros((480,640)); depth=np.zeros_like(ir)
        # 300-3/.5 = 294; 297-3/1 = 294. Nearest sample wins.
        ir[240,300]=111; depth[240,300]=.5; ir[240,297]=999; depth[240,297]=1.
        aligned,mask=register_ir_to_rgb(c,frame(c,'ir'),frame(c,'rgb'),ir,depth,max_skew_ns=2_000_000)
        self.assertEqual(mask.sum(),1); self.assertEqual(aligned[240,294],111)


if __name__=='__main__': unittest.main()
