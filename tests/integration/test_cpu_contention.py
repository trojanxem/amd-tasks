"""Integration test for CPU contention."""

from queue import Empty
from time import perf_counter

import pytest

from amd_tasks.contention.cpu import start_compression_jobs


def test_compression_respects_cpu_worker_limit(
    cpu_contention_fault: bool,
) -> None:
    """Compression should use a bounded number of CPU workers."""

    snapshot_count = 8
    worker_limit = 2

    start = perf_counter()

    processes, result_queue = start_compression_jobs(
        fault_enabled=cpu_contention_fault,
        snapshot_count=snapshot_count,
        worker_limit=worker_limit,
    )

    for process in processes:
        process.join(timeout=20)

    duration = perf_counter() - start

    blocked_processes = [process.name for process in processes if process.is_alive()]

    if blocked_processes:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join()

    assert not blocked_processes, (
        f"SCENARIO_ERROR[cpu-contention]: processes did not finish: {blocked_processes}"
    )

    failed_processes = [
        (process.name, process.exitcode) for process in processes if process.exitcode != 0
    ]

    assert not failed_processes, (
        f"SCENARIO_ERROR[cpu-contention]: process failures: {failed_processes}"
    )

    results = []

    try:
        for _ in range(snapshot_count):
            results.append(result_queue.get(timeout=2))
    except Empty:
        pytest.fail("SCENARIO_ERROR[cpu-contention]: missing compression results")
    finally:
        result_queue.close()
        result_queue.join_thread()

    switch_ids = {switch_id for switch_id, _, _ in results}

    assert switch_ids == set(range(snapshot_count)), (
        "SCENARIO_ERROR[cpu-contention]: incomplete compression results"
    )

    process_count = len(processes)

    print(
        f"CPU metrics: processes={process_count}, "
        f"snapshots={snapshot_count}, "
        f"duration={duration:.4f}s"
    )

    assert process_count <= worker_limit, (
        "FAULT_DETECTED[cpu-contention]: "
        f"started {process_count} CPU workers, "
        f"configured limit is {worker_limit}"
    )
