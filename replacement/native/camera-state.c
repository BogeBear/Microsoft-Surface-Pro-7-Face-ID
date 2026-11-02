// SPDX-License-Identifier: GPL-3.0-only
/* Project helper; 2026-11-02: verify an unchanged read-only crop explicitly. */
#include <linux/videodev2.h>
#include <linux/v4l2-subdev.h>
#include <sys/ioctl.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

/* Save and restore exact active formats for this local, same-boot test. */
struct state {
    uint32_t magic, subdev, pad, has_crop;
    struct v4l2_format video;
    struct v4l2_subdev_format format;
    struct v4l2_subdev_selection crop;
};
static int get(int fd, struct state *s) {
    if (!s->subdev) {
        s->video.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        return ioctl(fd, VIDIOC_G_FMT, &s->video);
    }
    s->format.which = V4L2_SUBDEV_FORMAT_ACTIVE;
    s->format.pad = s->pad;
    if (ioctl(fd, VIDIOC_SUBDEV_G_FMT, &s->format)) return -1;
    s->crop.which = V4L2_SUBDEV_FORMAT_ACTIVE;
    s->crop.pad = s->pad;
    s->crop.target = V4L2_SEL_TGT_CROP;
    if (ioctl(fd, VIDIOC_SUBDEV_G_SELECTION, &s->crop) == 0) s->has_crop = 1;
    else if (errno != EINVAL && errno != ENOTTY) return -1;
    return 0;
}
static int restore_crop(int fd, const struct v4l2_subdev_selection *saved)
{
    struct v4l2_subdev_selection request=*saved, observed=*saved;
    if (!ioctl(fd,VIDIOC_SUBDEV_S_SELECTION,&request)) return 0;
    if (errno!=ENOTTY) return -1;
    /* A fixed crop can be readable without having a setter. Accept only a
     * fresh exact readback; never reinterpret a failed format setter or I/O.
     */
    if (ioctl(fd,VIDIOC_SUBDEV_G_SELECTION,&observed)) return -1;
    if (observed.which!=saved->which || observed.pad!=saved->pad ||
        observed.target!=saved->target || observed.r.left!=saved->r.left ||
        observed.r.top!=saved->r.top || observed.r.width!=saved->r.width ||
        observed.r.height!=saved->r.height) {errno=ERANGE;return -1;}
    return 0;
}
int main(int argc, char **argv) {
    if (argc != 5) { fprintf(stderr,"save|restore|verify DEVICE STATEFILE video|PAD\n"); return 2; }
    struct state s = {.magic=0x49525333, .subdev=strcmp(argv[4],"video") != 0};
    if (s.subdev) {
        char *end; unsigned long pad = strtoul(argv[4], &end, 10);
        if (*end || pad > 15) return 2;
        s.pad = (uint32_t)pad;
    }
    int fd=open(argv[2],O_RDWR|O_NONBLOCK|O_CLOEXEC);
    if (fd<0) { perror("open camera"); return 1; }
    if (!strcmp(argv[1],"save")) {
        if (get(fd,&s)) { perror("read format"); close(fd); return 1; }
        FILE *f=fopen(argv[3],"wbx");
        if (!f) { perror("create snapshot"); close(fd); return 1; }
        int ok=fwrite(&s,sizeof s,1,f)==1;
        if (fclose(f)) ok=0;
        close(fd); return ok?0:1;
    }
    struct state saved={0}; FILE *f=fopen(argv[3],"rb");
    if (!f) { perror("read snapshot"); close(fd); return 1; }
    int ok=fread(&saved,sizeof saved,1,f)==1 && fgetc(f)==EOF; fclose(f);
    if (!ok || saved.magic!=s.magic || saved.subdev!=s.subdev || saved.pad!=s.pad) {
        fprintf(stderr,"Snapshot does not match target\n"); close(fd); return 1;
    }
    if (!strcmp(argv[1],"restore")) {
        struct state restore=saved;
        int rc=restore.subdev ? ioctl(fd,VIDIOC_SUBDEV_S_FMT,&restore.format) : ioctl(fd,VIDIOC_S_FMT,&restore.video);
        if (rc) {
            perror("restore format"); close(fd); return 1;
        }
        if (restore.has_crop && restore_crop(fd,&saved.crop)) {
            perror("restore crop"); close(fd); return 1;
        }
        /* BE source formats are derived from the current crop rectangle. */
        if (restore.has_crop) {
            restore.format=saved.format;
            if (ioctl(fd,VIDIOC_SUBDEV_S_FMT,&restore.format)) {
                perror("restore cropped source format"); close(fd); return 1;
            }
        }
    } else if (strcmp(argv[1],"verify")) { close(fd); return 2; }
    if (get(fd,&s)) { perror("reread format"); close(fd); return 1; }
    close(fd);
    ok=s.subdev ? !memcmp(&s.format.format,&saved.format.format,sizeof s.format.format) : !memcmp(&s.video,&saved.video,sizeof s.video);
    if (s.has_crop!=saved.has_crop || (s.has_crop && memcmp(&s.crop.r,&saved.crop.r,sizeof s.crop.r))) ok=0;
    if (!ok) fprintf(stderr,"Format verification differs: %s pad=%s\n",argv[2],argv[4]);
    return ok?0:1;
}
