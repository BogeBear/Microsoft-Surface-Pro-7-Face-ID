/* SPDX-License-Identifier: GPL-2.0-only */
/* Tests the SAME new adapter bodies compiled into the module, using injected
 * I/O and PM/scheduler substitutes. Not a physical sensor or real-time proof. */
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdarg.h>
#include <stddef.h>
#include <sys/types.h>
#include "ir_gate.h"
typedef long long s64;typedef int s32;
typedef unsigned char u8; typedef unsigned short u16;typedef unsigned int u32;
#define OV7251_SC_MODE_SELECT 0x0100
#define OV7251_SC_MODE_SELECT_SW_STANDBY 0
#define OV7251_TIMING_MIN_VTS 1
#define OV7251_TIMING_MAX_VTS 65535
#define DIV_ROUND_CLOSEST_ULL(a,b) (((a)+(b)/2)/(b))
#define system_wq 0
struct work_struct {int unused;};
struct mutex {int locked;};struct delayed_work {struct work_struct work;ir_time delay;bool active;};
struct v4l2_ctrl {long long minimum,maximum,step,default_value;struct {int val;}cur;};
struct ov7251_mode_info {unsigned int width,height,vts,data_size,exposure_max,exposure_def;const void *data;};
struct v4l2_fract {u32 numerator,denominator;};
struct ov7251 {
 struct ir_gate ir;struct mutex lock,request_lock;struct delayed_work ir_work;
 bool session_power,prepared,ready;void *dev,*ctrls;unsigned int link_freq_idx;
 const struct ov7251_mode_info *current_mode;
 struct v4l2_ctrl *hblank,*vblank,*exposure,*gain;
};
struct v4l2_subdev {struct ov7251 *sensor;};
static struct {u8 regs[65536];int count,fail,fail_again,pm,clock_us;ir_time clock;unsigned int writes,period_writes;} f;
static unsigned int checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"SESSION failed %d %s\n",__LINE__,#x);exit(1);}}while(0)
static int step(void){++f.count;return f.count==f.fail || f.count==f.fail_again ? -EIO : 0;}
static void mutex_lock(struct mutex *m){CHECK(!m->locked);m->locked=1;}
static void mutex_unlock(struct mutex *m){CHECK(m->locked);m->locked=0;}
static void cancel_delayed_work_sync(struct delayed_work *w){w->active=false;}
static void mod_delayed_work(int q,struct delayed_work *w,ir_time t){(void)q;w->active=true;w->delay=t;}
static ir_time ktime_get_ns(void){return f.clock;}
static ir_time nsecs_to_jiffies(ir_time n){return n/1000000;}
static int pm_runtime_resume_and_get(void *dev){int r=step();(void)dev;if(!r)f.pm++;return r;}
static void pm_runtime_mark_last_busy(void *dev){(void)dev;}
static void pm_runtime_put_autosuspend(void *dev){(void)dev;CHECK(f.pm>0);f.pm--;}
static void msleep(int n){f.clock+=n*1000000ULL;f.clock_us+=n*1000;}
static struct ov7251 *to_ov7251(struct v4l2_subdev *sd){return sd->sensor;}
static int ov7251_read_reg(void *s,u16 reg,u8 *v){int r=step();(void)s;if(!r)*v=f.regs[reg];return r;}
static int ov7251_write_reg(void *s,u16 reg,u8 v){int r=step();(void)s;if(!r){f.regs[reg]=v;f.writes++;if(reg==0x4837)f.period_writes++;}return r;}
static int ov7251_pll_configure(struct ov7251 *s){(void)s;return step();}
static int ov7251_set_register_array(struct ov7251 *s,const void *p,unsigned int n){(void)s;(void)p;(void)n;return step();}
static int __v4l2_ctrl_handler_setup(void *p){(void)p;return step();}
struct device {int unused;};
struct attribute {int unused;};
struct device_attribute {struct attribute attr;};
static struct v4l2_subdev *current_sd;
#define to_i2c_client(d) (d)
#define i2c_get_clientdata(d) ((void)(d),current_sd)
#define to_delayed_work(w) ((struct delayed_work *)(w))
#define container_of(p,type,member) ((type *)((char *)(p)-offsetof(type,member)))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define DEVICE_ATTR_RW(n) struct device_attribute dev_attr_##n
#define DEVICE_ATTR_RO(n) struct device_attribute dev_attr_##n
#define ATTRIBUTE_GROUPS(n) static void *n##_groups=(void *)n##_attrs
static bool delayed_work_pending(struct delayed_work *w){return w->active;}
static bool sysfs_streq(const char *a,const char *b){size_t n=strlen(b);return !strcmp(a,b)||(!strncmp(a,b,n)&&a[n]=='\n'&&!a[n+1]);}
static int sysfs_emit(char *buf,const char *fmt,...){int r;va_list a;va_start(a,fmt);r=vsnprintf(buf,4096,fmt,a);va_end(a);return r;}
static int sysfs_emit_at(char *buf,int offset,const char *fmt,...){int r;va_list a;va_start(a,fmt);r=vsnprintf(buf+offset,4096-offset,fmt,a);va_end(a);return r;}
#include "ir_bridge.inc"
static const unsigned int pixel_rates[]={48000000};
static unsigned int gcd(unsigned int a,unsigned int b){while(b){unsigned int t=a%b;a=b;b=t;}return a;}
static int __v4l2_ctrl_modify_range(struct v4l2_ctrl *c,long long a,long long b,long long stepv,long long d){int r=step();if(!r){c->minimum=a;c->maximum=b;c->step=stepv;c->default_value=d;}return r;}
static int __v4l2_ctrl_s_ctrl(struct v4l2_ctrl *c,int value){int r=step();if(!r)c->cur.val=value;return r;}
#include "ir_session.inc"
#include "ir_stream.inc"
#include "ir_mode.inc"
static void init(struct ov7251 *s,struct v4l2_subdev *sd){
 static struct v4l2_ctrl ctrls[4];
 static const struct ov7251_mode_info mode={640,480,1724,0,1704,504,NULL};
 memset(&f,0,sizeof(f));memset(s,0,sizeof(*s));memset(ctrls,0,sizeof(ctrls));
 s->current_mode=&mode;s->hblank=&ctrls[0];s->vblank=&ctrls[1];s->exposure=&ctrls[2];s->gain=&ctrls[3];
 s->hblank->cur.val=288;s->vblank->cur.val=1244;s->exposure->cur.val=504;s->gain->cur.val=16;
 s->vblank->maximum=65055;s->exposure->maximum=1704;
 f.regs[0x380c]=3;f.regs[0x380d]=160;f.regs[0x380e]=6;f.regs[0x380f]=188;
 s->ready=true;sd->sensor=s;current_sd=sd;
}
int main(void){
 struct ov7251 s;struct v4l2_subdev sd;unsigned int i,n;
 init(&s,&sd);CHECK(!ir_pre_stream(&sd,0));CHECK(s.prepared&&s.session_power&&f.pm==1);CHECK(f.clock_us==25000);
 n=f.count;CHECK(!ov7251_s_stream(&sd,1));CHECK(s.ir.stream&&f.pm==1);CHECK(f.count-n<20);CHECK(f.period_writes==1);
 {struct ir_bus b=ir_sensor_bus(&s);CHECK(!ir_gate_begin(&s.ir,&b));}
 CHECK(ov7251_s_stream(&sd,1)==-EBUSY);CHECK(s.ir_work.active);
 CHECK(ir_post_stream(&sd)==-EBUSY);CHECK(s.ir_work.active);CHECK(s.ir.armed);
 CHECK(!ov7251_s_stream(&sd,0));CHECK(!f.pm&&!s.session_power&&!s.ir.pending&&!s.ir.stream);
 CHECK(!ir_post_stream(&sd));CHECK(!s.ir_work.active);
 init(&s,&sd);s.ready=false;CHECK(ov7251_s_stream(&sd,1)==-EBUSY);CHECK(ir_pre_stream(&sd,0)==-EBUSY);CHECK(!f.count);
 init(&s,&sd);CHECK(ir_pre_stream(&sd,1)==-EINVAL);CHECK(!f.count);
 init(&s,&sd);CHECK(!ov7251_s_stream(&sd,1));n=f.count;CHECK(!ov7251_s_stream(&sd,0));
 for(i=1;i<=n;i++){
  init(&s,&sd);f.fail=i;CHECK(ov7251_s_stream(&sd,1)<0);CHECK(!s.ir.armed);
  if(s.session_power){CHECK(s.ir.fault&&s.ir.pending&&f.pm==1);f.fail=0;CHECK(!ov7251_s_stream(&sd,0));CHECK(s.ir.fault);}
  CHECK(f.pm==0);CHECK(!s.lock.locked&&!s.request_lock.locked);
 }
 init(&s,&sd);CHECK(!ov7251_s_stream(&sd,1));f.count=0;CHECK(!ov7251_s_stream(&sd,0));n=f.count;
 for(i=1;i<=n;i++){
  init(&s,&sd);CHECK(!ov7251_s_stream(&sd,1));f.count=0;f.fail=i;
  CHECK(ov7251_s_stream(&sd,0)<0);CHECK(f.pm==1&&s.ir.fault&&s.ir.pending&&s.session_power);
  f.fail=0;CHECK(!ov7251_s_stream(&sd,0));CHECK(f.pm==0&&s.ir.fault);
 }
 {struct ov7251_mode_info mode={640,480,860,0,840,504,NULL};struct v4l2_fract interval;
  init(&s,&sd);CHECK(!ir_select_mode(&s,&mode));CHECK(s.vblank->cur.val==380);ir_interval(&s,&interval);CHECK(interval.numerator&&interval.denominator);
  for(i=1;i<=5;i++){
   init(&s,&sd);f.fail=i;CHECK(ir_select_mode(&s,&mode)<0);CHECK(s.current_mode!=&mode);CHECK(s.vblank->cur.val==1244);CHECK(s.exposure->cur.val==504);CHECK(s.gain->cur.val==16);CHECK(!s.ir.fault);
  }
  init(&s,&sd);f.fail=1;f.fail_again=2;CHECK(ir_select_mode(&s,&mode)<0);CHECK(s.ir.fault);
  init(&s,&sd);s.session_power=true;CHECK(ir_select_mode(&s,&mode)==-EBUSY);CHECK(!f.count);
 }
 {char buf[4096];struct device dev={0};struct ir_bus b;
  CHECK(ir_groups!=NULL);
  init(&s,&sd);CHECK(ir_control_store(&dev,NULL,"capture",7)==-EHOSTDOWN);
  CHECK(ir_control_store(&dev,NULL,"arbitrary",9)==-EINVAL);CHECK(!f.count);
  CHECK(ir_snapshot_show(&dev,NULL,buf)==-EHOSTDOWN);CHECK(!f.count);
  CHECK(!ov7251_s_stream(&sd,1));
  CHECK(ir_control_store(&dev,NULL,"capture\n",8)==8);CHECK(s.ir_work.active&&s.ir.armed);
  CHECK(ir_control_store(&dev,NULL,"capture",7)==-EBUSY);CHECK(s.ir_work.active&&s.ir.armed);
  CHECK(ir_control_show(&dev,NULL,buf)>0);CHECK(strstr(buf,"armed=1")!=NULL);
  CHECK(ir_snapshot_show(&dev,NULL,buf)>0);CHECK(strstr(buf,"0100=01")!=NULL);
  CHECK(ir_strobe_test_show(&dev,NULL,buf)>0);CHECK(strstr(buf,"armed=1")!=NULL);
  f.clock=s.ir.deadline-1;s.ir_work.active=false;ir_deadline_work(&s.ir_work.work);CHECK(s.ir.armed&&s.ir_work.active);
  f.clock=s.ir.deadline;s.ir_work.active=false;ir_deadline_work(&s.ir_work.work);CHECK(!s.ir.armed&&!s.ir.pending);
  CHECK(ir_control_store(&dev,NULL,"off",3)==3);CHECK(!s.ir_work.active);
  CHECK(!ov7251_s_stream(&sd,0));
  CHECK(ir_strobe_test_show(&dev,NULL,buf)>0);CHECK(!strcmp(buf,"armed=0 remaining_ms=0 cleanup_pending=0 recovery_required=0\n"));
  init(&s,&sd);CHECK(!ov7251_s_stream(&sd,1));b=ir_sensor_bus(&s);CHECK(!ir_gate_begin(&s.ir,&b));
  s.ready=false;CHECK(ir_control_store(&dev,NULL,"capture",7)==-ENODEV);CHECK(s.ir_work.active);
 }
 printf("IR_SESSION_CHECKS=%u\n",checks);return 0;
}
