# Fault Injection & Detection

Five small examples with independently switchable faults and Pytest detectors.
Each implementation takes `fault_enabled=False`; setting it to `True` introduces
one defect in the same code path. No external service or test data is required.

## Setup and run

Requires Python **3.11+**. The code uses standard-library APIs available on Linux,
Windows, and macOS; CI is configured to test all three systems.

```sh
python -m venv .venv
```

Activate the environment with `source .venv/bin/activate` on Linux/macOS,
or `.venv\Scripts\Activate.ps1` in Windows PowerShell. Then:

```sh
python -m pip install -e ".[dev]"

# No flags: all scenarios use their fixed implementations.
python -m pytest -v -s

# Enable only I/O contention: its tests should FAIL with FAULT_DETECTED[io-contention].
python -m pytest -v -s --io-contention-fault

# Run only the CPU scenario with its fault enabled (expected FAILED).
python -m pytest -v -s tests/integration/test_cpu_contention.py --cpu-contention-fault
```

The flags are registered in `tests/conftest.py` and can be combined independently:

| Flag | Injected fault |
|---|---|
| `--race-fault` | TOCTOU race |
| `--deadlock-fault` | Circular-wait deadlock |
| `--thread-contention-fault` | Hot cache lock |
| `--io-contention-fault` | Excess I/O writers |
| `--cpu-contention-fault` | CPU starvation |

**Without flags: PASSED (exit 0). With a fault enabled: its test reports FAILED
(exit 1), reporting `FAULT_DETECTED[...]`.** Tests always check the same invariant;
flags change only the implementation. `-s` shows observed metrics.

For CI, a separate verification checks that each faulty implementation really
fails its integration test with the correct `FaultDetected` exception:

```sh
python -m pytest -v -s tests/verify_faults.py
```

This verification should pass. Missing detection, a different exception, corrupt
output, or a watchdog timeout makes it fail. The file is run explicitly so the
default run tests only fixed scenarios. CI runs both commands; the optional
`scripts/verify_faults.sh` wrapper runs the verification command.

## Defects, fixes, and detection

| Scenario | Root cause and symptom | Fix | Repeatable detection |
|---|---|---|---|
| TOCTOU race | Inventory disappears between `exists()` and `read_text()`; the read crashes | Read directly and handle `FileNotFoundError` | Remove a temporary file immediately before the read; expect `None` |
| Circular-wait deadlock | Two workers take inventory/state locks in opposite orders and stop | Use the same lock order | A barrier makes both hold their first lock; observe both waiting for the other's lock |
| Thread contention | Holding a shared cache lock during fetching serializes independent fetches | Fetch outside the cache lock | Hold fetch callbacks at a gate and count how many can enter concurrently |
| I/O contention | Too many snapshot writers wait behind a busy storage service, increasing request latency | Bound writers to the service capacity | Measure blocking on two service slots; detect an extra wait of at least one service interval |
| CPU contention | Bulk gzip compression monopolizes a shared event-loop thread and starves a small CPU request | Yield between chunks | Count bulk chunks processed before the foreground request gets CPU time |

The CPU example demonstrates **poor scheduling on one shared execution thread**.
Both tasks do real compression. With the fault, the foreground task must wait for
the entire batch; the fix lets it run after one chunk. This is a cooperative
scheduling example, not an OS scheduler benchmark. It needs no CPU affinity and
does not assume a particular core count or CPU speed.

The I/O test models a storage/network service with two slots and a minimum
20 ms service time per request, identical in both variants. A gate holds the
first occupied slots until all clients attempt access. Excess clients really
block on the semaphore; `monotonic()` measures their wait. The detector requires
an extra wait of at least one service interval (20 ms). The fixed variant has
no blocked requests. Slow writes alone do not trigger detection.
The backend also writes real temporary files and validates all records.
This measures queueing latency at a controlled service, not physical disk
throughput; a fast SSD or RAM-backed temporary directory is acceptable.

Expected metrics printed by the integration tests:

| Metric | Fixed | Injected |
|---|---:|---:|
| Concurrent fetches (2 / 4 workers) | 2 / 4 | 1 / 1 |
| Queued I/O requests (4 / 8 writers, 2 slots) | 0 / 0 | 2 / 6 |
| Maximum I/O slot wait | 0 ms | At least 20 ms |
| Bulk chunks delaying foreground CPU work (4 / 8 chunks) | 1 / 1 | 4 / 8 |
| Circular wait between two locks | False | True |
| TOCTOU file disappearance | Handled (`None`) | `FileNotFoundError` detected |

These thresholds follow from the controlled scheduling and service capacity,
rather than the evaluation machine's CPU or disk speed.
Events and barriers control the critical interleavings. Thread overlap has a
two-second observation window; process watchdogs allow 15 seconds. A severely
overloaded runner can still time out and should be investigated. Watchdog expiry
is never counted as successful fault detection.

## Structure and checks

- `src/amd_tasks/`: the five fault examples.
- `tests/integration/`: scheduling, output validation, and fault detection.
- `tests/verify_faults.py`: checks that injected faults fail the integration tests.
- `tests/helpers.py`: fault/scenario exceptions and portable process isolation using
  `multiprocessing` with `spawn`; blocked threads are terminated with their process.
- Other tests cover normal reads, backend failures, corrupt output, and cleanup.

Fetch, persistence, and compression callbacks can be replaced with other mocks or
real adapters. Their tests should retain output validation and use the adapter's
documented concurrency limits. The detectors target these specific defects; they
are not general-purpose concurrency profilers.

Thread and I/O workers use `ThreadPoolExecutor`: close the returned pool with
`with pool` and call `job.result()` for each job to propagate worker exceptions.

```sh
ruff check .
ruff format --check .
mypy src tests
```
