/* SPDX-License-Identifier: GPL-2.0-only */
/* SP7 project, 2026. New lifecycle core; callers serialize every operation. */
#ifndef SP7_IR_GATE_H
#define SP7_IR_GATE_H
#ifdef __KERNEL__
#include <linux/types.h>
#include <linux/errno.h>
typedef u64 ir_time;
#else
#include <stdint.h>
#include <errno.h>
typedef uint64_t ir_time;
#endif
#define IR_GATE_LIMIT_NS 3000000000ULL
struct ir_bus {
 void *context;
 int (*read)(void *, unsigned short, unsigned char *);
 int (*write)(void *, unsigned short, unsigned char);
 ir_time (*now)(void *);
};
struct ir_gate {
 unsigned int stream, consumed, pending, armed, fault;
 ir_time deadline;
 int first_error;
};
struct ir_register { unsigned short address; unsigned char value; };
int ir_gate_close(struct ir_gate *, const struct ir_bus *);
int ir_gate_begin(struct ir_gate *, const struct ir_bus *);
int ir_gate_tick(struct ir_gate *, const struct ir_bus *);
int ir_gate_stream(struct ir_gate *, const struct ir_bus *, int);
int ir_gate_reset(struct ir_gate *);
int ir_read_snapshot(const struct ir_bus *, struct ir_register *, unsigned int);
#endif
