#!/usr/bin/env python3

from bcc import BPF, PerfType, PerfSWConfig
import ctypes

# Experimental Stuff
#
# Use at your own risk.
#

bpf_text = r"""
#include <uapi/linux/ptrace.h>
#include <uapi/linux/bpf_perf_event.h>
#include <linux/sched.h>

struct data_t {
    u64 ts;
};

BPF_PERCPU_ARRAY(array, struct data_t, 1);
BPF_STACK_TRACE(stack_traces, 1024);
BPF_HASH(counts);

TRACEPOINT_PROBE(irq, irq_handler_entry)
{
    int zero = 0;
    struct data_t *ptr;
    struct data_t data = {};

    data.ts = bpf_ktime_get_ns();

    ptr = array.lookup(&zero);
    if (ptr && ptr->ts) {
        // do nothing
    } else {
        //bpf_trace_printk("enter\n");
        array.update(&zero, &data);
    }

    return 0;
}

TRACEPOINT_PROBE(irq, irq_handler_exit)
{
    int zero = 0;
    u64 ts = bpf_ktime_get_ns();
    struct data_t *ptr;
    struct data_t data = {};

    ptr = array.lookup(&zero);
    if (ptr && ptr->ts) {
        //bpf_trace_printk("exit (duration = %llu)\n", ts - ptr->ts);
        array.update(&zero, &data);
    }

    return 0;
}

#define THRESHOLD 1000000

int do_profile(struct bpf_perf_event_data *ctx)
{
    int zero = 0;
    u64 ts = bpf_ktime_get_ns();
    struct data_t *ptr;
    struct data_t data = {};

    ptr = array.lookup(&zero);
    if (ptr && ptr->ts && ts > ptr->ts + THRESHOLD) {
        int stackid = stack_traces.get_stackid(ctx, 0);
        //bpf_trace_printk("profile\n");
        counts.increment(stackid);
        array.update(&zero, &data);
    }

    return 0;
}
"""

b = BPF(text=bpf_text)
b.attach_perf_event(ev_type=PerfType.HARDWARE,
    ev_config=PerfSWConfig.CPU_CLOCK, fn_name="do_profile",
    sample_period=0, sample_freq=10000, cpu=-1)
try:
    # check /sys/kernel/debug/tracing/tracing_on
    b.trace_print()
except KeyboardInterrupt:
    print()
counts = b["counts"]
stack_traces = b["stack_traces"]
for k, v in sorted(counts.items(), key=lambda counts: counts[1].value):
    stack = stack_traces.walk(k.value)
    for frame in stack:
        print(b.ksym(frame).decode())
    print()
