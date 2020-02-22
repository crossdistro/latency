#!/usr/bin/env python3

import argparse
import struct

parser = argparse.ArgumentParser()
parser.add_argument("--delay", help="requested busy delay in milliseconds", type=int)
parser.add_argument("--syscall", help="run delay in a system call (the default)",
        dest="mode", action="store_const", const=0)
parser.add_argument("--kthread", help="run delay in a kernel thread",
        dest="mode", action="store_const", const=1)
parser.add_argument("--interrupt", "--irq", help="run delay in interrupt context",
        dest="mode", action="store_const", const=2)
parser.set_defaults(delay=1000, mode=0)
args = parser.parse_args()

with open("/dev/lat", "wb") as dev:
    dev.write(struct.pack("QQ", args.delay, args.mode))
