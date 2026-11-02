/* SPDX-License-Identifier: GPL-2.0-only */
/* SP7 project, 2026. Included after the licensed baseline register routines.
 * Lock order: request_lock -> sensor lock. Work only takes sensor lock.
 * This is a new API; old helpers must reject it until separately migrated.
 */
static int ir_bus_read(void *p, unsigned short reg, unsigned char *v)
{ return ov7251_read_reg(p, reg, v); }
static int ir_bus_write(void *p, unsigned short reg, unsigned char v)
{ return ov7251_write_reg(p, reg, v); }
static ir_time ir_bus_now(void *p) { return ktime_get_ns(); }
static struct ir_bus ir_sensor_bus(struct ov7251 *s)
{
 struct ir_bus b = { s, ir_bus_read, ir_bus_write, ir_bus_now };
 return b;
}

static void ir_deadline_work(struct work_struct *work)
{
 struct ov7251 *s = container_of(to_delayed_work(work), struct ov7251, ir_work);
 struct ir_bus b = ir_sensor_bus(s);
 ir_time now;
 mutex_lock(&s->lock);
 now = b.now(s);
 if (s->ir.armed && now < s->ir.deadline)
  mod_delayed_work(system_wq, &s->ir_work,
    nsecs_to_jiffies(s->ir.deadline - now) + 1);
 else if (s->session_power && (s->ir.armed || s->ir.pending))
  ir_gate_close(&s->ir, &b);
 mutex_unlock(&s->lock);
}

static ssize_t ir_control_show(struct device *dev, struct device_attribute *a, char *buf)
{
 struct ov7251 *s = to_ov7251(i2c_get_clientdata(to_i2c_client(dev)));
 ir_time n;
 ssize_t r;
 mutex_lock(&s->lock);
 n=ktime_get_ns();
 r = sysfs_emit(buf,
   "schema=sp7-independent-v1 stream=%u power_held=%u armed=%u pending=%u fault=%u error=%d consumed=%u remaining_ns=%llu\n",
   s->ir.stream, s->session_power, s->ir.armed, s->ir.pending,
   s->ir.fault, s->ir.first_error, s->ir.consumed,
   (unsigned long long)(s->ir.armed && s->ir.deadline > n ? s->ir.deadline - n : 0));
 mutex_unlock(&s->lock);
 return r;
}

static ssize_t ir_control_store(struct device *dev, struct device_attribute *a,
                                const char *buf, size_t count)
{
 struct ov7251 *s = to_ov7251(i2c_get_clientdata(to_i2c_client(dev)));
 struct ir_bus b = ir_sensor_bus(s);
 int r;
 bool capture = sysfs_streq(buf, "capture");
 if (!capture && !sysfs_streq(buf, "off")) return -EINVAL;
 mutex_lock(&s->request_lock);
 /* Synchronize without holding the lock taken by the worker. */
 cancel_delayed_work_sync(&s->ir_work);
 mutex_lock(&s->lock);
 if (!s->session_power) r = capture ? -EHOSTDOWN :
   (s->ir.pending || s->ir.fault ? -EIO : 0);
 else if (capture && !s->ready) r=-ENODEV;
 else if (capture) {
  r = ir_gate_begin(&s->ir, &b);

 } else r = ir_gate_close(&s->ir, &b);
 /* A rejected second capture must not cancel the first capture's timeout. */
 if (s->ir.armed && !delayed_work_pending(&s->ir_work)) {
  ir_time now = ktime_get_ns();
  if (now >= s->ir.deadline) ir_gate_close(&s->ir, &b);
  else mod_delayed_work(system_wq, &s->ir_work,
                        nsecs_to_jiffies(s->ir.deadline - now) + 1);
 }
 mutex_unlock(&s->lock);
 mutex_unlock(&s->request_lock);
 return r ? r : (ssize_t)count;
}
static DEVICE_ATTR_RW(ir_control);

static ssize_t ir_snapshot_show(struct device *dev, struct device_attribute *a, char *buf)
{
 struct ov7251 *s = to_ov7251(i2c_get_clientdata(to_i2c_client(dev)));
 struct ir_bus b = ir_sensor_bus(s);
 /* Fixed read-only list: mode, pad, PLLs, timing, MIPI and strobe gates.
  * Raw values carry no inferred physical clock rate or exposure time.
  */
 struct ir_register regs[] = {
  {0x0100,0}, {0x3005,0}, {0x3027,0}, {0x30b0,0}, {0x30b1,0}, {0x30b3,0}, {0x30b4,0}, {0x30b5,0}, {0x3098,0}, {0x3099,0}, {0x309a,0}, {0x309b,0}, {0x309d,0}, {0x3500,0}, {0x3501,0}, {0x3502,0}, {0x3503,0}, {0x350a,0}, {0x350b,0}, {0x380c,0}, {0x380d,0}, {0x380e,0}, {0x380f,0}, {0x4800,0}, {0x4837,0}, {0x3b80,0}, {0x3b81,0}, {0x3b82,0}, {0x3b83,0}, {0x3b84,0}, {0x3b85,0}, {0x3b86,0}, {0x3b87,0}, {0x3b88,0}, {0x3b89,0}, {0x3b8a,0}, {0x3b8b,0}, {0x3b8c,0}, {0x3b8d,0}, {0x3b8e,0}, {0x3b8f,0}, {0x3b90,0}, {0x3b91,0}, {0x3b92,0}, {0x3b93,0}, {0x3b94,0}, {0x3b95,0}, {0x3b96,0}, {0x3b97,0}
 };
 int r;
 unsigned int i;
 ssize_t len = 0;
 mutex_lock(&s->lock);
 if (!s->session_power || !s->ir.stream) { r = -EHOSTDOWN; goto done; }
 r = ir_read_snapshot(&b, regs, ARRAY_SIZE(regs));
 if (r) goto done;
 len = sysfs_emit(buf, "schema=sp7-independent-raw-v1");
 for (i=0; i<ARRAY_SIZE(regs); i++)
  len += sysfs_emit_at(buf, len, " %04x=%02x", regs[i].address, regs[i].value);
 len += sysfs_emit_at(buf, len, "\n");
 done:
 mutex_unlock(&s->lock);
 return r ? r : len;
}
static DEVICE_ATTR_RO(ir_snapshot);
/* Read-only compatibility for the existing full idle inventory. No old
 * write/arm interface is exposed. All eight PM states remain separate checks.
 */
static ssize_t ir_strobe_test_show(struct device *dev,struct device_attribute *a,char *buf)
{
 struct ov7251 *s=to_ov7251(i2c_get_clientdata(to_i2c_client(dev)));
 ir_time now;
 ssize_t r;
 mutex_lock(&s->lock);
 now=ktime_get_ns();
 r=sysfs_emit(buf,"armed=%u remaining_ms=%llu cleanup_pending=%u recovery_required=%u\n",
   s->ir.armed,(unsigned long long)(s->ir.armed && s->ir.deadline>now ? (s->ir.deadline-now)/1000000 : 0),
   s->ir.pending,s->ir.fault);
 mutex_unlock(&s->lock);return r;
}
static DEVICE_ATTR_RO(ir_strobe_test);
static struct attribute *ir_attrs[] = {
 &dev_attr_ir_control.attr, &dev_attr_ir_snapshot.attr, &dev_attr_ir_strobe_test.attr, NULL
};
ATTRIBUTE_GROUPS(ir);
