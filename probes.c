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
