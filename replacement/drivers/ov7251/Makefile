# SPDX-License-Identifier: GPL-2.0-only
ifneq ($(KERNELRELEASE),)
ifneq ($(KERNELRELEASE),7.2.11-arch1-1-surface)
$(error Unsupported kernel ABI; expected 7.2.11-arch1-1-surface)
endif
obj-m += ov7251.o
ov7251-y := sensor.o ir_gate.o
else
KDIR ?= /lib/modules/7.2.11-arch1-1-surface/build
.PHONY: all clean
all:
	$(MAKE) -C $(KDIR) M=$(CURDIR) modules
clean:
	$(MAKE) -C $(KDIR) M=$(CURDIR) clean
endif
