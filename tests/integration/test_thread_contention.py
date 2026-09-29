"""Hold fetches at a controlled point to measure their overlap."""

from threading import Event, Lock

import pytest

from amd_tasks.contention.thread import start_inventory_workers


@pytest.mark.parametrize("worker_count", [2, 4])
def test_inventory_fetches_run_concurrently(thread_contention_fault, worker_count):
    release = Event()
    all_started = Event()
    counter_lock = Lock()
    started = 0

    def fetch(worker_id):
        nonlocal started
        with counter_lock:
            started += 1
            if started == worker_count:
                all_started.set()
        release.wait()
        return {"switch": f"switch-{worker_id}", "ports": 48}

    pool, jobs, cache = start_inventory_workers(fetch, thread_contention_fault, worker_count)
    with pool:
        try:
            all_started.wait(timeout=2)
            with counter_lock:
                concurrent = started
        finally:
            release.set()
        for job in jobs:
            job.result()
    assert cache == {i: {"switch": f"switch-{i}", "ports": 48} for i in range(worker_count)}
    print(f"Threads: {concurrent}/{worker_count} fetches overlap")
    assert concurrent == worker_count, (
        f"FAULT_DETECTED[thread-contention]: only {concurrent} concurrent fetches"
    )
