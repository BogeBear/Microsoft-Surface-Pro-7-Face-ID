/* SPDX-License-Identifier: GPL-2.0-only */
/* New cached-mode transaction; no sensor I/O is permitted during this operation. */
struct ir_ctrl_saved { s64 minimum, maximum, step, def; s32 value; };
static int ir_select_mode(struct ov7251 *s,const struct ov7251_mode_info *mode)
{
 struct v4l2_ctrl *ctrls[]={s->vblank,s->exposure,s->gain};
 struct ir_ctrl_saved old[3];
 const struct ov7251_mode_info *previous=s->current_mode;
 int i,r=0,restore=0,q;
 if(s->session_power || s->ir.pending || s->ir.fault) return -EBUSY;
 if(previous==mode) return 0;
 for(i=0;i<3;i++) old[i]=(struct ir_ctrl_saved){ctrls[i]->minimum,
   ctrls[i]->maximum,ctrls[i]->step,ctrls[i]->default_value,ctrls[i]->cur.val};
 s->current_mode=mode;
 r=__v4l2_ctrl_modify_range(s->vblank,OV7251_TIMING_MIN_VTS,
     OV7251_TIMING_MAX_VTS-mode->height,1,mode->vts-mode->height);
 if(!r) r=__v4l2_ctrl_s_ctrl(s->vblank,mode->vts-mode->height);
 if(!r) r=__v4l2_ctrl_modify_range(s->exposure,1,mode->exposure_max,1,mode->exposure_def);
 if(!r) r=__v4l2_ctrl_s_ctrl(s->exposure,mode->exposure_def);
 if(!r) r=__v4l2_ctrl_s_ctrl(s->gain,16);
 if(!r) return 0;
 s->current_mode=previous;
 /* VBLANK first; its callback can change exposure's range. */
 for(i=0;i<3;i++) {
  q=__v4l2_ctrl_modify_range(ctrls[i],old[i].minimum,old[i].maximum,old[i].step,old[i].def);
  if(q && !restore) restore=q;
  q=__v4l2_ctrl_s_ctrl(ctrls[i],old[i].value);
  if(q && !restore) restore=q;
 }
 if(restore) {s->ir.fault=1;if(!s->ir.first_error)s->ir.first_error=restore;}
 return r;
}
static void ir_interval(struct ov7251 *s,struct v4l2_fract *out)
{
 u32 clocks=(s->current_mode->width+s->hblank->cur.val)*
             (s->current_mode->height+s->vblank->cur.val);
 u32 rate=pixel_rates[s->link_freq_idx],div=gcd(clocks,rate);
 out->numerator=clocks/div;out->denominator=rate/div;
}
