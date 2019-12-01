#!/usr/bin/python3

from bcc import BPF
import contextlib
import struct

b = BPF(src_file="probes.c")

class Stats:
    def __init__(self):
        self.sum = 0
        self.count = 0
        self.min = float("+inf")
        self.max = float("-inf")

    def add(self, value):
        self.sum += value
        self.count += 1
        if value < self.min:
            self.min = value
        if value > self.max:
            self.max = value

    def handle_event(self, cpu, data, size):
        event = b["events"].event(data)
        self.add(event.latency / 1000)

    @property
    def avg(self):
        return self.sum / self.count

stats = Stats()

b["events"].open_perf_buffer(stats.handle_event)

with contextlib.suppress(KeyboardInterrupt):
    b.kprobe_poll()

print(f"{stats.min:.3f} {stats.avg:.3f} {stats.max:.3f}")
