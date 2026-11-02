# SPDX-License-Identifier: GPL-3.0-only
"""Strict logical graph comparison across one normal sensor re-registration.
Only numeric entity IDs and entity listing order may change. All entity names,
pad text, device nodes, links, flags and global headers remain exact.
Only ID-width-dependent indentation of type/device description lines is ignored.
This is a recovery-boundary check, never a capture restoration substitute.
"""
import re
def canonical(graph):
    if not isinstance(graph,str) or len(graph)>262144:raise ValueError('Invalid graph')
    parts=graph.split('- entity ')
    if len(parts)<2:raise ValueError('No entities')
    entities={};ids=set()
    for part in parts[1:]:
        match=re.match(r'([0-9]+): (.+?) \(',part)
        if not match:raise ValueError('Invalid entity header')
        identity,name=match.groups()
        if identity in ids or name in entities:raise ValueError('Duplicate entity')
        ids.add(identity)
        normalized=re.sub(r'^[0-9]+:', 'ID:',part,count=1)
        normalized=re.sub(r'(?m)^ +(?=(?:type |device node name ))', ' ',normalized)
        entities[name]=normalized.rstrip('\n')
    return {'header':parts[0],'entities':entities}
def verify(old,new):
    if canonical(old)!=canonical(new):raise ValueError('Logical media graph changed')
    return {'logical_graph_verified':True,'numeric_entity_ID_or_listing_order_may_differ':True,'capture_restoration_contract_changed':False}
