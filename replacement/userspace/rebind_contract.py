# SPDX-License-Identifier: GPL-3.0-only
"""Normal driver rebind after independently proved quiescence; no forced load.
This never enables capture/light or clears an existing project hold.
"""
def rebind(io):
    result={'verified':False,'unbound':False,'rebound':False,'errors':[]}
    try:
        io.check_binding()
        result['before']=io.full_idle()
        io.verify_preconditions()
        result['before_unbind']=io.full_idle()
        io.check_binding()
        io.unbind()
        result['unbound']=True
        io.verify_detached()
        io.bind_device()
        result['rebound']=True
        io.check_binding()
        io.verify_original_settings()
        result['after']=io.full_idle()
        result['verified']=True
    except BaseException as error:
        result['errors'].append(type(error).__name__+': '+str(error))
    result['capture_authorized']=False
    result['external_root_exit_required']=True
    return result
