MAKE_MODULES = make -C /lib/modules/$(shell uname -r)/build M=$(shell pwd)
MODULE = lat

ccflags-y += -DDEBUG
obj-m = $(MODULE).o

all:
	$(MAKE_MODULES)
clean:
	$(MAKE_MODULES) clean
insmod: all
	sudo rmmod $(MODULE) 2>/dev/null || true
	sudo insmod $(MODULE).ko
	sudo bash -c 'chown "$${SUDO_UID}:root" /dev/$(MODULE)'
