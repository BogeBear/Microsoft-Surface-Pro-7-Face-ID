/* SPDX-License-Identifier: GPL-2.0-only */
static int ov7251_s_stream(struct v4l2_subdev *sd, int enable)
{
 struct ov7251 *s=to_ov7251(sd);
 struct ir_bus bus=ir_sensor_bus(s);
 u8 actual=0xff;
 int r=0;
 mutex_lock(&s->request_lock);
 cancel_delayed_work_sync(&s->ir_work);
 mutex_lock(&s->lock);
 if(enable) {
  if(!s->ready || s->ir.stream || s->ir.fault || s->ir.pending) {r=-EBUSY;goto done;}
  if(!s->session_power) {
   r=pm_runtime_resume_and_get(s->dev);
   if(r<0) goto done;
   s->session_power=true;
  }
  if(!s->prepared) r=ir_prepare_sensor(s);
  if(!r) r=ir_gate_stream(&s->ir,&bus,1);
  if(!r) r=ov7251_write_reg(s,0x0100,1);
  if(!r) r=ov7251_read_reg(s,0x0100,&actual);
  if(!r && actual!=1) r=-EIO;
  if(r) ir_session_stop(s);
  else s->prepared=false;
 } else r=ir_session_stop(s);
 done:
 if(s->ir.armed) {
  ir_time now=ktime_get_ns();
  if(now>=s->ir.deadline) ir_gate_close(&s->ir,&bus);
  else mod_delayed_work(system_wq,&s->ir_work,nsecs_to_jiffies(s->ir.deadline-now)+1);
 }
 mutex_unlock(&s->lock);mutex_unlock(&s->request_lock);return r;
}
