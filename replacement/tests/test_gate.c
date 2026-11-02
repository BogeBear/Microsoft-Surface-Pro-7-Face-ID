/* SPDX-License-Identifier: GPL-2.0-only */
/* New independent specification tests. No extraction of old driver functions. */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "ir_gate.h"
struct fake {
 unsigned char regs[65536];
 unsigned int n,fail,mode,writes; ir_time clock,advance;
 unsigned short touched[256]; unsigned char values[256];
};
static int rd(void *p,unsigned short a,unsigned char *v) {
 struct fake *f=p;f->n++;f->clock+=f->advance;
 if(f->n==f->fail) { if(f->mode==2){*v=0xff;return 0;} return -EIO; }
 *v=f->regs[a];return 0;
}
static int wr(void *p,unsigned short a,unsigned char v) {
 struct fake *f=p;f->n++;f->clock+=f->advance;
 f->touched[f->writes]=a;f->values[f->writes++]=v;
 if(f->n==f->fail && f->mode!=1) return -EIO;
 f->regs[a]=v;
 return f->n==f->fail ? -EIO : 0;
}
static ir_time now(void *p){return ((struct fake*)p)->clock;}
static unsigned int checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"failed line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
static void fresh(struct fake *f,struct ir_gate *g,struct ir_bus *b) {
 memset(f,0,sizeof(*f));memset(g,0,sizeof(*g));
 f->regs[0x3005]=0xa0;f->regs[0x3b80]=0x65;f->regs[0x3b96]=0x40;
 *b=(struct ir_bus){f,rd,wr,now};
}
int main(void) {
 struct fake f;struct ir_gate g;struct ir_bus b;unsigned int i,j;
 fresh(&f,&g,&b);
 CHECK(ir_gate_begin(&g,&b)==-EBUSY);CHECK(f.n==0);
 CHECK(!ir_gate_stream(&g,&b,1));CHECK(g.stream&&!g.pending&&!g.fault);
 CHECK(ir_gate_stream(&g,&b,1)==-EBUSY);
 CHECK(!ir_gate_begin(&g,&b));CHECK(g.armed&&g.pending&&g.consumed);
 CHECK(f.regs[0x3b96]==0xc0);CHECK(f.regs[0x3005]==0xa8);CHECK(f.regs[0x3b80]==0x75);
 CHECK(ir_gate_begin(&g,&b)==-EBUSY);
 f.clock=g.deadline-1;CHECK(!ir_gate_tick(&g,&b));CHECK(g.armed);
 f.clock++;CHECK(!ir_gate_tick(&g,&b));CHECK(!g.armed&&!g.pending);
 CHECK(f.regs[0x3005]==0xa0&&f.regs[0x3b80]==0x65&&f.regs[0x3b96]==0x40);
 CHECK(ir_gate_begin(&g,&b)==-EBUSY);CHECK(!ir_gate_stream(&g,&b,0));
 CHECK(!ir_gate_stream(&g,&b,1));CHECK(!ir_gate_begin(&g,&b));
 CHECK(!ir_gate_stream(&g,&b,0));CHECK(!g.stream&&!g.pending);
 CHECK(!ir_gate_reset(&g));
 /* Exhaust all failure positions in enable including cleanup; writes may
  * fail after actually changing the emulated device. */
 for(j=0;j<3;j++)for(i=1;i<=9;i++) {
  if(j==2 && i!=3 && i!=6 && i!=9) continue; /* Corrupt confirmation, not the input observation. */
  fresh(&f,&g,&b);CHECK(!ir_gate_stream(&g,&b,1));f.n=0;f.fail=i;f.mode=j;
  CHECK(ir_gate_begin(&g,&b)<0);CHECK(g.fault&&!g.armed&&g.consumed);
  CHECK(!g.pending);CHECK(!(f.regs[0x3005]&8));CHECK(!(f.regs[0x3b80]&16));CHECK(!(f.regs[0x3b96]&128));
  CHECK(ir_gate_begin(&g,&b)==-EBUSY);
  CHECK(ir_gate_reset(&g)==-EBUSY); /* Stream still owns power. */
  CHECK(!ir_gate_stream(&g,&b,0));CHECK(g.fault);CHECK(!ir_gate_reset(&g));
 }
 /* Fail every shutdown I/O; any missing confirmation remains pending. */
 for(i=1;i<=9;i++) {
  fresh(&f,&g,&b);CHECK(!ir_gate_stream(&g,&b,1));CHECK(!ir_gate_begin(&g,&b));
  f.n=0;f.fail=i;
  CHECK(ir_gate_close(&g,&b)<0);CHECK(g.fault&&g.pending&&!g.armed);
  CHECK(ir_gate_reset(&g)==-EBUSY);
  f.fail=0;CHECK(!ir_gate_close(&g,&b));CHECK(!g.pending&&g.fault);
  CHECK(!ir_gate_stream(&g,&b,0));CHECK(!ir_gate_reset(&g));
 }
 fresh(&f,&g,&b);CHECK(!ir_gate_stream(&g,&b,1));f.clock=(ir_time)-1;
 CHECK(ir_gate_begin(&g,&b)==-ERANGE);CHECK(!g.armed&&!g.consumed);
 fresh(&f,&g,&b);CHECK(!ir_gate_stream(&g,&b,1));f.advance=IR_GATE_LIMIT_NS;
 CHECK(ir_gate_begin(&g,&b)==-ETIME);CHECK(g.fault&&!g.armed&&!g.pending);
 /* Confirm writes never change other registers or gate-unrelated bits. */
 for(i=0;i<256;i++) {
  fresh(&f,&g,&b);f.regs[0x3005]=(unsigned char)i;f.regs[0x3b80]=(unsigned char)~i;f.regs[0x3b96]=(unsigned char)(i^90);
  CHECK(!ir_gate_stream(&g,&b,1));CHECK(!ir_gate_begin(&g,&b));CHECK(!ir_gate_close(&g,&b));
  for(j=0;j<f.writes;j++)CHECK(f.touched[j]==0x3005||f.touched[j]==0x3b80||f.touched[j]==0x3b96);
  CHECK((f.regs[0x3005]&~8)==(i&~8));
  CHECK((f.regs[0x3b80]&~16)==((unsigned char)~i&~16));
  CHECK((f.regs[0x3b96]&~128)==((i^90)&~128));
 }
 {struct ir_register regs[2]={{0x3005,0},{0x3b80,0}};
  fresh(&f,&g,&b);CHECK(ir_read_snapshot(&b,regs,0)==-EINVAL);
  CHECK(ir_read_snapshot(&b,regs,65)==-EINVAL);CHECK(!f.n);
  CHECK(!ir_read_snapshot(&b,regs,2));CHECK(regs[0].value==0xa0);
  f.fail=f.n+2;CHECK(ir_read_snapshot(&b,regs,2)==-EIO);CHECK(!f.writes);
 }
 printf("IR_GATE_CHECKS=%u\n",checks);return 0;
}
