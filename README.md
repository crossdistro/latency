# Experimental latency tracing code

I have just started experimenting with eBPF tracing (Nov 2019) and this
project contains the results of my latency tracing experiments.

## Limitations

  * Not targeting high performance right now
  * Ignoring all data that we don't manage to pass to userspace

## Spinlock tracing

Using a debug kernel (with `CONFIG_DEBUG_SPINLOCK`) we trace the following
functions:

  * `_raw_spin_lock()`
  * `_raw_spin_unlock()`

We pair the calls by the `raw_spinlock_t` memory address between the two
calls. Therefore we have the latencies for all lock/unlock pairs for raw
spinlocks.
