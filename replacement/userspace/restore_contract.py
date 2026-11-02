# SPDX-License-Identifier: GPL-3.0-only
"""Restoration only. Never authorizes capture, illumination or a reset.
Caller must bind the failed session, originals, root package and actual device.
"""
def restore(io, original):
    result={'restored':False,'errors':[],'before':None,'after':None}
    try:
        io.bind_restore()
        result['before']=io.full_idle()
        io.disconnect_original_trial_links()
        for record in original['snapshots']:
            io.bind_restore()
            io.restore_format(record)
        # Verify every record after ALL mutations, including cross-pad effects.
        for record in original['snapshots']:
            io.bind_restore()
            io.verify_format(record)
        io.verify_controls(original['sensor_controls'])
        io.verify_graph(original['graph'])
        result['after']=io.full_idle()
        result['restored']=True
    except BaseException as error:
        result['errors'].append(type(error).__name__+': '+str(error))
    result['root_exit_and_external_idle_required']=True
    result['capture_authorized']=False
    return result
