# SPDX-License-Identifier: GPL-3.0-only
import hashlib,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import uint8_detector as u

class Net:
    def __init__(self): self.output=np.array([[[[0,1,.95,.1,.2,.8,.9]]]],np.float32)
    def setInput(self,x): self.input=x
    def forward(self): return self.output
class DNN:
    def __init__(self): self.net=Net()
    def readNetFromTensorflow(self,w,c): self.loaded=(bytes(w),bytes(c));return self.net
    def blobFromImage(self,*a,**kw): self.blob_args=(a,kw);return a[0]
class CV:
    COLOR_RGB2BGR=7
    def __init__(self):self.dnn=DNN()
    def cvtColor(self,x,code):return x[:,:,::-1]
class Tests(unittest.TestCase):
    def setUp(self):
        self.cv=CV();self.image=np.zeros((640,480,3),np.uint8)
        with patch.object(u,'checked_bytes',side_effect=[b'weights',b'config']):
            self.det=u.Uint8Detector('w','c',cv=self.cv)
    def test_exact_buffers_loaded(self):self.assertEqual(self.cv.dnn.loaded,(b'weights',b'config'))
    def test_proposal_and_preprocessing(self):
        r=self.det.detect(self.image);self.assertTrue(r['single_face_candidate']);self.assertFalse(r['authentication_allowed']);self.assertTrue(r['password_required']);self.assertFalse(r['PAD_verified']);self.assertAlmostEqual(r['faces'][0]['box_xyxy'][2],384,places=3)
        self.assertEqual(self.cv.dnn.blob_args[0][2],(300,300));self.assertEqual(self.cv.dnn.blob_args[0][3],(104,177,123))
    def test_nonfinite_malformed_or_oversized(self):
        for x in [np.zeros((1,1,0,7)),np.zeros((1,1,1001,7)),np.zeros((1,7)),np.full((1,1,1,7),np.nan)]:
            self.cv.dnn.net.output=x
            with self.assertRaises(ValueError):self.det.detect(self.image)
    def test_class_box_batch_score_validation(self):
        for idx,val in [(0,1),(1,2),(2,1.1),(3,-.1),(5,1.2),(5,.05)]:
            self.cv.dnn.net.output=np.array([[[[0,1,.95,.1,.2,.8,.9]]]],np.float32)
            self.cv.dnn.net.output[0,0,0,idx]=val
            with self.assertRaises(ValueError):self.det.detect(self.image)
    def test_multiple_faces_remain_ambiguous(self):
        self.cv.dnn.net.output=np.repeat(self.cv.dnn.net.output,2,axis=2)
        self.assertTrue(self.det.detect(self.image)['multiple_faces'])
    def test_empty_result_and_sentinel(self):
        self.cv.dnn.net.output[0,0,0,2]=.1;self.assertFalse(self.det.detect(self.image)['single_face_candidate'])
        self.cv.dnn.net.output[0,0,0,0]=-1;self.assertEqual(self.det.detect(self.image)['faces'],[])
    def test_invalid_inputs(self):
        for image in [self.image.astype(np.float32),np.zeros((16,16),np.uint8),np.zeros((1,16,3),np.uint8)]:
            with self.assertRaises(ValueError):self.det.detect(image)
        for threshold in [True,0.0,1.0,float('nan')]:
            with self.assertRaises(ValueError):self.det.detect(self.image,confidence=threshold)
    def test_guard_failure_does_not_infer(self):
        def bad():raise RuntimeError('thermal stop')
        self.det.guard=bad
        with self.assertRaises(RuntimeError):self.det.detect(self.image)
        self.assertFalse(hasattr(self.cv.dnn.net,'input'))
    def test_verified_regular_input_and_rejections(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'model';p.write_bytes(b'good');p.chmod(0o600)
            sha=hashlib.sha256(b'good').hexdigest();self.assertEqual(u.checked_bytes(p,sha,4),b'good')
            for expected,cap in [('0'*64,4),(sha,3)]:
                with self.assertRaises(ValueError):u.checked_bytes(p,expected,cap)
            p.chmod(0o666)
            with self.assertRaises(ValueError):u.checked_bytes(p,sha,4)
            p.chmod(0o600);alias=Path(td)/'alias';alias.symlink_to(p)
            with self.assertRaises(OSError):u.checked_bytes(alias,sha,4)
            alias.unlink();os.link(p,alias)
            with self.assertRaises(ValueError):u.checked_bytes(p,sha,4)
    def test_read_changes_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'m';p.write_bytes(b'good');p.chmod(0o600);original=os.read
            def changing(fd,n):
                x=original(fd,n)
                if x:p.write_bytes(b'evil')
                return x
            with patch.object(u.os,'read',side_effect=changing):
                with self.assertRaises(ValueError):u.checked_bytes(p,hashlib.sha256(b'good').hexdigest(),4)
if __name__=='__main__':unittest.main()
