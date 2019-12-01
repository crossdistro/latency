#!/usr/bin/python3

from bcc import BPF
import contextlib
import struct

bpf_text = r"""
#include <uapi/linux/ptrace.h>
#include <linux/irq.h>
#include <linux/spinlock.h>

struct event {
    u64 latency;
};

BPF_PERF_OUTPUT(events);
BPF_HASH(locks);

int kprobe___raw_spin_lock(struct pt_regs *ctx, u64 lock)
{
    u64 zero = 0;
    u64 *value;

    locks.insert(&lock, &zero);
    value = locks.lookup(&lock);
    if (value)
        (*value) = bpf_ktime_get_ns();
    return 0;
}

int kprobe___raw_spin_unlock(struct pt_regs *ctx, u64 lock)
{
    u64 *value;

    if ((value = locks.lookup(&lock))) {
        struct event event = {
            .latency = bpf_ktime_get_ns() - *value,
        };
        events.perf_submit(ctx, &event, sizeof event);
    }
    bpf_trace_printk("unlock %ld %ld\n", lock, value ? *value : 42);
    return 0;
}
"""

b = BPF(text=bpf_text)

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
