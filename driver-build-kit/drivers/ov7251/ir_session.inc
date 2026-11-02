/* SPDX-License-Identifier: GPL-2.0-only */
/* New SP7 preparation/stream lifecycle. Included after control routines.
 * Baseline mode tables are retained byte-for-byte. The pixel-period field
 * is expressed in half-nanosecond units in datasheet table 7-17; this is
 * configured metadata, not independent physical-clock measurement.
 */
static int ir_read_word(struct ov7251 *s, u16 reg, u16 *out)
{
 u8 hi, lo;
 int r = ov7251_read_reg(s,reg,&hi);
 if (!r) r=ov7251_read_reg(s,reg+1,&lo);
 if (!r) *out=((u16)hi<<8)|lo;
 return r;
}
static int ir_prepare_sensor(struct ov7251 *s)
{
 struct ir_bus b=ir_sensor_bus(s);
 u8 mode=0xff, period;
 u16 hts,vts;
 unsigned int configured_period=DIV_ROUND_CLOSEST_ULL(2000000000ULL,pixel_rates[s->link_freq_idx]);
 int r;
 if (!configured_period || configured_period>255) return -ERANGE;
 r=ov7251_pll_configure(s);
 if (!r) r=ov7251_set_register_array(s,s->current_mode->data,s->current_mode->data_size);
 if (!r) r=ov7251_write_reg(s,0x4837,configured_period);
 if (!r) r=__v4l2_ctrl_handler_setup(&s->ctrls);
 if (!r) r=ir_gate_close(&s->ir,&b);
 if (!r) r=ov7251_write_reg(s,OV7251_SC_MODE_SELECT,OV7251_SC_MODE_SELECT_SW_STANDBY);
 if (!r) r=ov7251_read_reg(s,0x0100,&mode);
 if (!r) r=ir_read_word(s,0x380c,&hts);
 if (!r) r=ir_read_word(s,0x380e,&vts);
 if (!r) r=ov7251_read_reg(s,0x4837,&period);
 if (!r && (mode!=0 || hts!=s->current_mode->width+s->hblank->cur.val ||
     vts!=s->current_mode->height+s->vblank->cur.val || period!=configured_period)) r=-EIO;
 return r;
}

/* Caller holds request_lock and lock. Always attempt both independent stops. */
static int ir_session_stop(struct ov7251 *s)
{
 struct ir_bus b=ir_sensor_bus(s);
 u8 mode=0xff;
 int closed, written, readback, r;
 if (!s->session_power) return s->ir.fault ? -EIO : 0;
 closed=ir_gate_stream(&s->ir,&b,0);
 written=ov7251_write_reg(s,0x0100,0);
 readback=ov7251_read_reg(s,0x0100,&mode);
 r=closed ? closed : written ? written : readback ? readback : mode ? -EIO : 0;
 if (r) {
  s->ir.fault=1;s->ir.pending=1;
  if (!s->ir.first_error) s->ir.first_error=r;
  /* Retain the PM reference. A later attempt can close, but not erase fault. */
 } else {
  s->prepared=false;s->session_power=false;
  pm_runtime_mark_last_busy(s->dev);
  pm_runtime_put_autosuspend(s->dev);
 }
 return r;
}

static int ir_pre_stream(struct v4l2_subdev *sd, u32 flags)
{
 struct ov7251 *s=to_ov7251(sd);
 int r;
 if (flags) return -EINVAL; /* Software standby is not a measured LP-11 claim. */
 mutex_lock(&s->request_lock);
 mutex_lock(&s->lock);
 if (!s->ready || s->session_power || s->ir.fault || s->ir.pending) {r=-EBUSY;goto done;}
 r=pm_runtime_resume_and_get(s->dev);
 if(r<0) goto done;
 s->session_power=true;
 r=ir_prepare_sensor(s);
 if(!r) {msleep(25);s->prepared=true;}
 else ir_session_stop(s);
 done: mutex_unlock(&s->lock);mutex_unlock(&s->request_lock);return r;
}
static int ir_post_stream(struct v4l2_subdev *sd)
{
 struct ov7251 *s=to_ov7251(sd);
 int r;
 mutex_lock(&s->request_lock);
 cancel_delayed_work_sync(&s->ir_work);
 mutex_lock(&s->lock);
 /* Never cancel the running stream's watchdog as a side effect of refusal. */
 if(s->ir.stream) {
  struct ir_bus b=ir_sensor_bus(s);
  ir_time now=ktime_get_ns();
  r=-EBUSY;
  if(s->ir.armed) {
   if(now>=s->ir.deadline) ir_gate_close(&s->ir,&b);
   else mod_delayed_work(system_wq,&s->ir_work,nsecs_to_jiffies(s->ir.deadline-now)+1);
  }
 } else r=ir_session_stop(s);
 mutex_unlock(&s->lock);mutex_unlock(&s->request_lock);return r;
}
