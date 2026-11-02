#!/usr/bin/env python3
"""CLI for saved RGB/IR point correspondences. Never opens a camera or PAM."""
import argparse
from dataclasses import fields
import json
import os
from pathlib import Path

from stereo import Frame, calibrate, digest, triangulate


def reconstruct(request):
    if request.get('schema') != 'sp7-correspondences-v1':
        raise ValueError('Unknown correspondence request')
    calibration = request['calibration']
    if request.get('calibration_sha256') != digest(calibration):
        raise ValueError('Calibration content binding mismatch')
    if request.get('correspondence_source') not in ('known-target', 'synthetic', 'manually-reviewed'):
        raise ValueError('Correspondence provenance required')
    permitted = {f.name for f in fields(Frame)}
    def frame(key):
        record = request[key]
        if set(record) != permitted:
            raise ValueError('Frame metadata must contain exactly the required fields')
        return Frame(**record)
    result = triangulate(calibration, frame('ir_frame'), frame('rgb_frame'),
        request['ir_points_px'], request['rgb_points_px'], max_skew_ns=request['max_skew_ns'])
    result['correspondence_source'] = request['correspondence_source']
    result['request_sha256'] = digest(request)
    return result


def write_private(path, data):
    # New destinations only. Never overwrite evidence or existing results.
    descriptor = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as output:
        output.write(json.dumps(data, indent=2, allow_nan=False)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('triangulate', 'calibrate'))
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.input.stat().st_size > 32*1024*1024:
        raise ValueError('Input exceeds offline request limit')
    request = json.loads(args.input.read_text())
    if args.operation == 'triangulate': result = reconstruct(request)
    else:
        if request.get('schema') != 'sp7-target-views-v1': raise ValueError('Unknown calibration request')
        result = calibrate(request['ir_spec'], request['rgb_spec'], request['object_views_m'],
            request['ir_views_px'], request['rgb_views_px'], target_id=request['target_id'], source=request['source'])
        result['request_sha256'] = digest(request)
    write_private(args.output, result)
    print('Offline geometry report written; no authentication performed.')


if __name__ == '__main__': main()
