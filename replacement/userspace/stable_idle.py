"""Bounded re-read of a failed transient process inventory; never accept unknown.

The fixed reader's full two-pass scan, identity/sharing/visibility/holder,
boot/catalog/power/strobe and four-second bounds are unchanged. A subsequent
independent complete scan is required. Observed camera, permission, metadata
limit, namespace, reuse and unknown errors stop immediately. No capture retry.
"""
import json
TRANSIENT=('FileNotFoundError:', 'process_inventory_changed:',
           'task_inventory_changed:', 'task_inventory_changed_between_passes',
           'task_exited_during_proc_stat:', 'thread_inventory_unstable_after_3_attempts:')
PREFIX='unstable_process_inventory_after_2_attempts:'
def full_idle(io,clock,sleep):
 start=clock();attempts=0
 while attempts<3:
  left=8-(clock()-start)
  if not 0<left<=8:raise RuntimeError('Full idle aggregate deadline')
  io.bind();io.cool();attempts+=1
  reply=io.inspect_once(min(4.5,left));io.record_idle_attempt(reply)
  if clock()-start>=8:raise RuntimeError('Full idle aggregate deadline')
  if reply.get('stderr'):raise RuntimeError('Inspector warning; visibility unknown')
  try:j=json.loads(reply['stdout'])
  except (KeyError,TypeError,ValueError):raise RuntimeError('Malformed inspector receipt') from None
  if reply.get('exit')==0 and j.get('complete') is True:
   io.validate_snapshot(j)
   if all(v=='suspended' for v in j['power'].values()):
    io.validate(j)
    return j
   # This is a complete, fresh observation of a known non-idle state,
   # not a missing/failed read. A later COMPLETE read must prove suspended.
   if attempts>=3:raise RuntimeError('Devices did not suspend within three full reads')
   sleep(.1)
   continue
  reason=j.get('reason','')
  if (reply.get('exit')!=2 or j.get('complete') is not False or
      not isinstance(reason,str) or not reason.startswith(PREFIX) or
      not reason[len(PREFIX):].startswith(TRANSIENT) or
      'camera_seen' in reason):raise RuntimeError('Unretryable incomplete client inventory: '+str(reason))
  if attempts>=3:raise RuntimeError('No complete client snapshot after three bounded reads: '+reason)
  sleep(.1)
 raise RuntimeError('No complete client receipt')
