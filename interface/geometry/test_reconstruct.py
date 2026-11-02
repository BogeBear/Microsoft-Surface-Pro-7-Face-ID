import copy
from dataclasses import asdict
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

from reconstruct import reconstruct, write_private
from stereo import digest
from test_stereo import fixture, frame, project
import numpy as np


def request():
    c=fixture(); a,b=project(c,np.array([[0.,0.,.6]]))
    return {'schema':'sp7-correspondences-v1', 'calibration':c, 'calibration_sha256':digest(c),
        'correspondence_source':'synthetic', 'ir_frame':asdict(frame(c,'ir')), 'rgb_frame':asdict(frame(c,'rgb')),
        'ir_points_px':a.tolist(), 'rgb_points_px':b.tolist(), 'max_skew_ns':2_000_000}


class CliTests(unittest.TestCase):
    def test_request_reconstructs_and_remains_non_authentication(self):
        r=reconstruct(request()); self.assertEqual(r['valid_points'],1); self.assertFalse(r['authentication_granted'])
    def test_changed_calibration_fails_binding(self):
        r=request(); r['calibration']['ir']['K'][0][0]+=10
        with self.assertRaises(ValueError): reconstruct(r)
    def test_unknown_correspondence_source_rejected(self):
        r=request(); r['correspondence_source']='assumed'
        with self.assertRaises(ValueError): reconstruct(r)
    def test_missing_frame_field_rejected(self):
        r=request(); del r['ir_frame']['clock_id']
        with self.assertRaises(ValueError): reconstruct(r)
    def test_private_output_and_existing_evidence_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'report.json'; write_private(p,{'first':True})
            self.assertEqual(stat.S_IMODE(p.stat().st_mode),0o600)
            with self.assertRaises(FileExistsError): write_private(p,{'first':False})
            self.assertTrue(json.loads(p.read_text())['first'])
    def test_actual_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'request.json'; dst=Path(tmp)/'result.json'
            src.write_text(json.dumps(request()))
            p=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('reconstruct.py')),
                'triangulate','--input',str(src),'--output',str(dst)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertEqual(json.loads(dst.read_text())['valid_points'],1)
            self.assertNotIn('point_ir_m',p.stdout)


if __name__=='__main__': unittest.main()
