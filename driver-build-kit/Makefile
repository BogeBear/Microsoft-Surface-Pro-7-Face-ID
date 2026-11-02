# SPDX-License-Identifier: GPL-2.0-only
# Explicit out-of-tree build only. No install, signing or loading target.
export LC_ALL := C
KERNEL_RELEASE := 7.2.11-arch1-1-surface
KDIR ?= /lib/modules/$(KERNEL_RELEASE)/build
ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
IPU := $(ROOT)/drivers/ipu4/drivers/media/pci/intel/ipu4
.PHONY: all check-headers ov7251 int3472 ipu4
all: ov7251 int3472 ipu4
check-headers:
	@test "$$(make -s -C "$(KDIR)" kernelrelease)" = "$(KERNEL_RELEASE)" || { echo 'Exact reviewed kernel headers required' >&2; exit 1; }
ov7251: check-headers
	$(MAKE) -C "$(KDIR)" M="$(ROOT)/drivers/ov7251" modules
int3472: check-headers
	$(MAKE) -C "$(KDIR)" M="$(ROOT)/drivers/int3472" modules
ipu4: check-headers
	$(MAKE) -C "$(KDIR)" M="$(IPU)" KCFLAGS="-I$(ROOT)/drivers/ipu4/include -I$(ROOT)/drivers/ipu4/include/uapi" srcpath="$(IPU)" EXTERNAL_BUILD=1 CONFIG_VIDEO_INTEL_IPU=m CONFIG_VIDEO_INTEL_IPU4P=y CONFIG_VIDEO_INTEL_IPU_FW_LIB=y modules
