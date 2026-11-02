/* SPDX-License-Identifier: GPL-2.0-only */
/* SP7 project, 2026. Register facts: OV7750/OV7251 rev1F v2.12, tables
 * 2-3 and 7-9. No frequency/duty, frame-pattern, span, current or polarity tuning.
 * STROBE source-enable is gated separately; all other bits are preserved.
 * The board safety policy and power/stream ownership live in the adapter.
 */
#include "ir_gate.h"
#define PAD_DIRECTION 0x3005
#define FRAME_TRIGGER 0x3b80
#define STROBE_SOURCE 0x3b96
#define SOURCE_MASK 0x80
#define PAD_MASK 0x08
#define TRIGGER_MASK 0x10

static int fault(struct ir_gate *g, int e)
{
 g->fault = 1;
 if (!g->first_error) g->first_error = e;
 return e;
}

/* A failed write can have reached the device: always attempt readback. */
static int change(const struct ir_bus *b, unsigned short reg,
                  unsigned char mask, int on)
{
 unsigned char before, after, target;
 int r, w;
 r = b->read(b->context, reg, &before);
 if (r) return r;
 target = on ? (before | mask) : (before & (unsigned char)~mask);
 w = b->write(b->context, reg, target);
 r = b->read(b->context, reg, &after);
 if (w) return w;
 if (r) return r;
 return after == target ? 0 : -EIO;
}

int ir_gate_close(struct ir_gate *g, const struct ir_bus *b)
{
 int a, source, z;
 g->armed = 0;
 /* Close the pad even if the source gate fails. All three independent readbacks are required. */
 a = change(b, PAD_DIRECTION, PAD_MASK, 0);
 source = change(b, STROBE_SOURCE, SOURCE_MASK, 0);
 z = change(b, FRAME_TRIGGER, TRIGGER_MASK, 0);
 if (a || source || z) {
  g->pending = 1;
  return fault(g, a ? a : source ? source : z);
 }
 g->pending = 0;
 return 0; /* Sticky fault is intentionally NOT cleared by a later close. */
}

int ir_gate_begin(struct ir_gate *g, const struct ir_bus *b)
{
 ir_time start;
 int r;
 if (!g->stream || g->consumed || g->pending || g->armed || g->fault)
  return -EBUSY;
 start = b->now(b->context);
 if (start > (ir_time)-1 - IR_GATE_LIMIT_NS) return -ERANGE;
 g->consumed = 1;
 g->deadline = start + IR_GATE_LIMIT_NS;
 g->pending = 1; /* Set before the first possibly effective write. */
 r = change(b, FRAME_TRIGGER, TRIGGER_MASK, 1);
 if (!r && b->now(b->context) < g->deadline)
  r = change(b, STROBE_SOURCE, SOURCE_MASK, 1);
 else if (!r) r = -ETIME;
 if (!r && b->now(b->context) < g->deadline)
  r = change(b, PAD_DIRECTION, PAD_MASK, 1);
 else if (!r) r = -ETIME;
 if (!r && b->now(b->context) >= g->deadline) r = -ETIME;
 if (r) {
  fault(g, r);
  ir_gate_close(g, b);
  return r;
 }
 g->armed = 1;
 return 0;
}

int ir_gate_tick(struct ir_gate *g, const struct ir_bus *b)
{
 if ((g->armed || g->pending) && b->now(b->context) >= g->deadline)
  return ir_gate_close(g, b);
 return 0;
}

int ir_gate_stream(struct ir_gate *g, const struct ir_bus *b, int enabled)
{
 int r;
 if (enabled) {
  if (g->stream || g->fault || g->pending) return -EBUSY;
  r = ir_gate_close(g, b);
  if (r) return r;
  g->stream = 1;
  g->consumed = 0;
  return 0;
 }
 r = ir_gate_close(g, b);
 g->stream = 0;
 return r;
}

/* Only a caller with independent full-off/reset evidence may invoke this.
 * Resetting fields is not itself evidence. No sysfs reset command is supplied.
 */
int ir_gate_reset(struct ir_gate *g)
{
 if (g->stream || g->pending || g->armed) return -EBUSY;
 g->fault = 0;
 g->first_error = 0;
 g->consumed = 0;
 g->deadline = 0;
 return 0;
}

/* Callers supply a fixed register list, bounded at 64; no writable interface. */
int ir_read_snapshot(const struct ir_bus *b, struct ir_register *regs, unsigned int n)
{
 unsigned int i;
 int r;
 if (!n || n > 64) return -EINVAL;
 for (i = 0; i < n; ++i) {
  r = b->read(b->context, regs[i].address, &regs[i].value);
  if (r) return r; /* Caller must discard the whole partial snapshot. */
 }
 return 0;
}
