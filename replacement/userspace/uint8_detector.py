# SPDX-License-Identifier: GPL-3.0-only
"""Hash-bound UINT8 proposal backend. No camera or authentication operation.
Model weights remain external under their own license. No Caffe fallback.
"""
from pathlib import Path
import hashlib
import math
import os
import stat

WEIGHTS_SHA256 = '5c71d752ef2cbf2f457ac82fdd580fcb2522fd04c5efdaed18eb6d9e2843fbed'
CONFIG_SHA256 = 'ca0eb6b3a0e0b124282d093a3d8a9d453967f37af3c1a933978ac55605a8f2cb'
WEIGHTS_BYTES = 2727750


def checked_bytes(path, expected, maximum):
    """Load the exact verified bytes, not a path OpenCV might reopen later."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ValueError('Model input must be a regular file with one link')
        if before.st_mode & 0o022 or not 0 < before.st_size <= maximum:
            raise ValueError('Unsafe model file mode or size')
        data = bytearray()
        while len(data) <= maximum:
            chunk = os.read(fd, min(65536, maximum + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        after = os.fstat(fd)
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_mode', 'st_nlink')
        if any(getattr(before, k) != getattr(after, k) for k in fields):
            raise ValueError('Model input changed during verification')
        if len(data) != before.st_size or hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Unexpected model input identity')
        return bytes(data)
    finally:
        os.close(fd)


class Uint8Detector:
    def __init__(self, weights, config, *, cv=None, guard=None):
        if cv is None:
            import cv2 as cv
        self.cv = cv
        self.guard = guard or (lambda: None)
        self.guard()
        weight_data = checked_bytes(weights, WEIGHTS_SHA256, WEIGHTS_BYTES)
        config_data = checked_bytes(config, CONFIG_SHA256, 256 * 1024)
        import numpy as np
        # OpenCV accepts byte buffers; inference uses exactly the hashed input.
        self.net = cv.dnn.readNetFromTensorflow(np.frombuffer(weight_data, dtype=np.uint8),
                                               np.frombuffer(config_data, dtype=np.uint8))
        self.guard()

    def detect(self, rgb, *, confidence=0.8):
        import numpy as np
        if (not isinstance(rgb, np.ndarray) or rgb.dtype != np.uint8 or
                rgb.ndim != 3 or rgb.shape[2] != 3 or
                not 16 <= rgb.shape[0] <= 4096 or not 16 <= rgb.shape[1] <= 4096):
            raise ValueError('Expected a bounded uint8 RGB image')
        if type(confidence) is not float or not math.isfinite(confidence) or not 0 < confidence < 1:
            raise ValueError('Invalid diagnostic confidence threshold')
        self.guard()
        blob = self.cv.dnn.blobFromImage(self.cv.cvtColor(rgb, self.cv.COLOR_RGB2BGR),
                    1.0, (300, 300), (104, 177, 123), swapRB=False, crop=False)
        self.net.setInput(blob)
        output = self.net.forward()
        self.guard()
        if (not isinstance(output, np.ndarray) or output.ndim != 4 or
                output.shape[:2] != (1, 1) or output.shape[3] != 7 or
                not 0 < output.shape[2] <= 1000 or not np.isfinite(output).all()):
            raise ValueError('Invalid detector output')
        faces = []
        h, w = rgb.shape[:2]
        for row in output[0, 0]:
            batch, label, score = map(float, row[:3])
            # OpenCV DetectionOutput can emit -1 sentinel records.
            if batch == -1:
                continue
            if batch != 0 or not 0 <= score <= 1:
                raise ValueError('Invalid detector batch or score')
            if score < confidence:
                continue
            if label != 1:
                raise ValueError('Unexpected proposal class')
            x0, y0, x1, y1 = map(float, row[3:])
            if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
                raise ValueError('Proposal outside accepted field')
            faces.append({'box_xyxy': [x0*w, y0*h, x1*w, y1*h], 'score': score,
                          'score_is_identity_probability': False})
        return {'backend': 'opencv-tensorflow-uint8', 'faces': faces,
                'single_face_candidate': len(faces) == 1, 'multiple_faces': len(faces) > 1,
                'authentication_allowed': False, 'password_required': True, 'PAD_verified': False,
                'weights_sha256': WEIGHTS_SHA256, 'configuration_sha256': CONFIG_SHA256}
