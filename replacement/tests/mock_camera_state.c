/* SPDX-License-Identifier: GPL-3.0-only */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <sys/ioctl.h>
#include <linux/videodev2.h>
#include <linux/v4l2-subdev.h>
#include <stdarg.h>
#include <errno.h>
#include <string.h>
#include <stdlib.h>
static int attempted;
int ioctl(int fd,unsigned long request,...){
 va_list args;void *arg;const char *mode=getenv("MOCK_STATE_MODE");(void)fd;
 va_start(args,request);arg=va_arg(args,void*);va_end(args);
 if(!mode){errno=EPERM;return -1;}
 if(request==VIDIOC_SUBDEV_G_FMT){struct v4l2_subdev_format *f=arg;memset(&f->format,0,sizeof(f->format));f->format.width=640;f->format.height=480;f->format.code=0x200a;return 0;}
 if(request==VIDIOC_SUBDEV_S_FMT){if(!strcmp(mode,"format-error")){errno=EIO;return -1;}return 0;}
 if(request==VIDIOC_SUBDEV_G_SELECTION){
  struct v4l2_subdev_selection *s=arg;
  if(attempted&&!strcmp(mode,"readback-error")){errno=EIO;return -1;}
  s->r=(struct v4l2_rect){0,0,640,480};if(attempted&&!strcmp(mode,"mismatch"))s->r.width=638;return 0;
 }
 if(request==VIDIOC_SUBDEV_S_SELECTION){attempted=1;if(!strcmp(mode,"writable"))return 0;errno=!strcmp(mode,"selection-error")?EIO:ENOTTY;return -1;}
 errno=ENOTTY;return -1;
}
