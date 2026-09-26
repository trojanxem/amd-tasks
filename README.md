# Fault Injection & Detection

Small Python project demonstrating common concurrency and performance faults
together with deterministic detection tests.

## Setup

Create and activate the virtual environment:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
```

Install the project and development dependencies:

```bash
pip install -e ".[dev]"
```

## Running tests

Run all tests with the fixed implementations:

```bash
pytest -v
```

All tests should pass.

Run all fault-detection checks:

```bash
bash scripts/verify_faults.sh
```

The script enables each fault separately and verifies that the corresponding
test fails for the expected reason.

## Fault flags

Each scenario has two modes:

```text
no fault flag
→ fixed implementation
→ test passes

fault flag enabled
→ buggy implementation
→ same test fails
```

Available flags:

```text
--race-fault
--deadlock-fault
--thread-contention-fault
--io-contention-fault
--cpu-contention-fault
```

The fault flags only switch between the fixed and buggy implementations.
The test expectation stays the same.

---

## TOCTOU race condition

The inventory reader accesses a file that may disappear between checking that
it exists and actually reading it.

### Bug

```text
exists() -> True
       |
       | file removed
       v
read() -> FileNotFoundError
```

The fixed implementation reads the file directly and handles
`FileNotFoundError`.

The test deterministically removes a real temporary file immediately before
the read operation.

Run fixed:

```bash
pytest -v tests/integration/test_toctou.py
```

Expected:

```text
PASSED
```

Enable the fault:

```bash
pytest -v tests/integration/test_toctou.py --race-fault
```

Expected:

```text
FAILED
FAULT_DETECTED[toctou]
```

---

## Circular-wait deadlock

Two threads operate on inventory and synchronization state.

The fixed implementation always acquires locks in the same order:

```text
inventory_lock -> sync_state_lock
```

The faulty implementation reverses the order in one worker:

```text
inventory writer:   inventory_lock -> sync_state_lock
fetch-state writer: sync_state_lock -> inventory_lock
```

This creates a circular wait.

A `Barrier` makes the deadlock deterministic.
The scenario runs in a separate process so the watchdog can terminate it
after detecting the deadlock.

Run fixed:

```bash
pytest -v tests/integration/test_deadlock.py
```

Expected:

```text
PASSED
```

Enable the fault:

```bash
pytest -v tests/integration/test_deadlock.py --deadlock-fault
```

Expected:

```text
FAILED
FAULT_DETECTED[deadlock]
```

---

## Thread contention

Multiple workers fetch switch inventory and update a shared cache.

The fixed implementation performs the expensive fetch outside the cache lock:

```text
fetch -> cache_lock -> cache update
```

The faulty implementation holds the cache lock during the fetch:

```text
cache_lock -> fetch -> cache update
```

This creates a hot lock and serializes work that should run concurrently.

The test measures how many workers can enter the fetch operation at the same
time and also verifies that all workers finish successfully.

Run fixed:

```bash
pytest -v tests/integration/test_thread_contention.py
```

Expected:

```text
PASSED
```

Enable the fault:

```bash
pytest -v tests/integration/test_thread_contention.py \
    --thread-contention-fault
```

Expected:

```text
FAILED
FAULT_DETECTED[thread-contention]
```

---

## I/O contention

Multiple workers persist switch inventory snapshots to disk.

The faulty implementation performs a synchronous disk flush for every small
inventory record:

```text
write -> flush -> fsync
write -> flush -> fsync
write -> flush -> fsync
...
```

This creates excessive synchronous disk I/O when several writers run at the
same time.

The fixed implementation batches the complete snapshot and performs one
synchronous flush:

```text
write complete snapshot -> flush -> fsync
```

The test performs real file writes and real `fsync()` calls.
It counts synchronous flushes as the deterministic detection signal and also
reports execution time as a diagnostic metric.

Run fixed:

```bash
pytest -v -s tests/integration/test_io_contention.py
```

Expected:

```text
PASSED
```

Enable the fault:

```bash
pytest -v -s tests/integration/test_io_contention.py \
    --io-contention-fault
```

Expected:

```text
FAILED
FAULT_DETECTED[io-contention]
```

---

## CPU contention

Inventory snapshots are compressed before archival.

The fixed implementation uses a bounded number of CPU workers:

```text
8 snapshots
     |
     v
2 compression processes
```

The faulty implementation starts one CPU-bound process for every snapshot:

```text
8 snapshots
     |
     v
8 compression processes
```

The processes perform real inventory serialization and gzip compression.

The detector verifies that the configured CPU worker limit is respected.
Execution time is reported as a diagnostic metric but is not used as the main
CI threshold because runtime depends on the host hardware.

Run fixed:

```bash
pytest -v -s tests/integration/test_cpu_contention.py
```

Expected:

```text
PASSED
```

Enable the fault:

```bash
pytest -v -s tests/integration/test_cpu_contention.py \
    --cpu-contention-fault
```

Expected:

```text
FAILED
FAULT_DETECTED[cpu-contention]
```

---

## CI

GitHub Actions runs:

```text
Code quality
Unit tests
Integration tests
Fault detection
```

Normal tests run against the fixed implementations and must pass.

The fault-detection job enables each faulty implementation separately and
checks for its specific `FAULT_DETECTED[...]` marker.

This prevents unrelated test failures from being reported as successful fault
detection.
