# SPDX-License-Identifier: GPL-3.0-only
"""Single in-stream request and auditable readbacks, never standby arming.
No pulse/current/duty/frequency/span/pattern setter. Pixel scene consent and
native/kernel/root/idle evidence are separate requirements.
"""
from independent_status import parse
import re
ADDRESSES=[0x0100,0x3005,0x3027,0x30b0,0x30b1,0x30b3,0x30b4,0x30b5,0x3098,0x3099,0x309a,0x309b,0x309d,0x3500,0x3501,0x3502,0x3503,0x350a,0x350b,0x380c,0x380d,0x380e,0x380f,0x4800,0x4837]+list(range(0x3b80,0x3b98))
def raw(text):
    parts=text.split();values={}
    if not parts or parts[0]!='schema=sp7-independent-raw-v1':raise ValueError('Raw schema')
    for token in parts[1:]:
        if not re.fullmatch('[0-9a-f]{4}=[0-9a-f]{2}',token):raise ValueError('Raw token')
        key,val=token.split('=');address=int(key,16)
        if address not in ADDRESSES or key in values:raise ValueError('Unexpected raw inventory')
        values[key]=int(val,16)
    if set(values)!={f'{a:04x}' for a in ADDRESSES}:raise ValueError('Incomplete raw inventory')
    return values
def verify_enabled(before,after):
    expected=dict(before)
    if before['0100']!=1 or any(before[k]&mask for k,mask in [('3005',8),('3b80',16),('3b96',128)]):raise ValueError('Fresh dark streaming gates required')
    for key,mask in [('3005',8),('3b80',16),('3b96',128)]:expected[key]|=mask
    if after!=expected:raise ValueError('Enable changed unrelated registers or failed readback')
def arm(io):
    start=io.now_ns()
    while True:
        io.guard();state=parse(io.status())
        if state['stream'] and state['power_held']:break
        if io.now_ns()-start>800_000_000 or not io.workers_alive():raise ValueError('No bounded native stream')
        io.sleep(.01)
    if not state['light_closure_fields_clear'] or state['consumed']:raise ValueError('One fresh request required')
    before=io.snapshot();begin=io.now_ns();io.capture();after_state=io.status();after=io.snapshot();end=io.now_ns()
    active=parse(after_state)
    if not active['armed'] or not active['remaining_ns'] or active['fault']:raise ValueError('No active request readback')
    verify_enabled(raw(before),raw(after))
    if not 0<=end-begin<3_000_000_000:raise ValueError('Request observation exceeded deadline')
    return dict(begin_ns=begin,end_ns=end,before_raw=before,enabled_raw=after,enabled_status=after_state,optical_emission_verified=False)
def verify_receipts(metadata):
    arm=metadata['running_light_arm'];verify_enabled(raw(arm['before_raw']),raw(arm['enabled_raw']))
    active=parse(arm['enabled_status']);closed=parse(metadata['post_native_control'])
    if not active['armed'] or active['consumed']!=1 or active['remaining_ns']<=0:raise ValueError('Missing enable receipt')
    if not closed['session_released'] or not closed['light_closure_fields_clear'] or closed['remaining_ns'] or closed['consumed']!=1:raise ValueError('Incomplete light/session release')
    off=metadata['post_native_dark']
    if off.get('light_off_verified') is not True or off.get('after')!='armed=0 remaining_ms=0 cleanup_pending=0 recovery_required=0':raise ValueError('No explicit off receipt')
    if not 0<arm['begin_ns']<=arm['end_ns']<=metadata['post_native_dark_ns'] or metadata['post_native_dark_ns']-arm['begin_ns']>=3_200_000_000:raise ValueError('Light receipt time bounds')
    return dict(three_gate_enable_readbacks_verified=True,native_stop_and_explicit_off_verified=True,unrelated_PWM_timing_registers_preserved=True,optical_emission_verified=False)
