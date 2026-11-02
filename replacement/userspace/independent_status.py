# SPDX-License-Identifier: GPL-3.0-only
"""Parser for the new driver API. Status alone is NEVER a full idle receipt."""
import re

FIELDS={'stream','power_held','armed','pending','fault','error','consumed','remaining_ns'}


def parse(text):
    if type(text) is not str or len(text)>512:
        raise ValueError('Invalid status size')
    tokens=text.split()
    if not tokens or tokens[0]!='schema=sp7-independent-v1':
        raise ValueError('Unsupported driver status')
    result={}
    for token in tokens[1:]:
        if not re.fullmatch(r'[a-z_]+=-?[0-9]{1,20}',token):
            raise ValueError('Invalid status field')
        k,value=token.split('=')
        if k in result or k not in FIELDS:
            raise ValueError('Unexpected or repeated status field')
        result[k]=int(value)
    if set(result)!=FIELDS:
        raise ValueError('Incomplete status')
    for k in FIELDS-{'remaining_ns','error'}:
        if result[k] not in (0,1):
            raise ValueError('Invalid boolean state')
    if not -4095<=result['error']<=0 or not 0<=result['remaining_ns']<=3_000_000_000:
        raise ValueError('Invalid error or deadline')
    if result['armed'] and not all(result[k] for k in ['stream','power_held','pending','consumed']):
        raise ValueError('Contradictory active state')
    if result['stream'] and not result['power_held']:
        raise ValueError('Stream without power reference')
    if bool(result['error'])!=bool(result['fault']):
        raise ValueError('Contradictory sticky error')
    result['light_closure_fields_clear']=not any(result[k] for k in ['armed','pending','fault'])
    result['session_released']=not result['stream'] and not result['power_held']
    result['full_idle_verified']=False
    result['authentication_allowed']=False
    return result
