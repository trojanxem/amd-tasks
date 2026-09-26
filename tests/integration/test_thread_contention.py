"""Integration test for thread contention."""

from threading import Event, Lock

from amd_tasks.contention.thread import start_inventory_workers


def test_inventory_fetches_run_concurrently(
    thread_contention_fault: bool,
) -> None:
    """Inventory workers should fetch concurrently."""

    worker_count = 4

    release_fetch = Event()
    all_fetches_started = Event()

    started_lock = Lock()
    started_count = 0

    def fetch_inventory(worker_id: int) -> dict:
        nonlocal started_count

        with started_lock:
            started_count += 1

            if started_count == worker_count:
                all_fetches_started.set()

        # Do not release automatically.
        # The test controls exactly when fetches may continue.
        release_fetch.wait()

        return {
            "switch": f"switch-{worker_id}",
            "ports": 48,
        }

    threads, cache, errors = start_inventory_workers(
        fetch_inventory=fetch_inventory,
        fault_enabled=thread_contention_fault,
        worker_count=worker_count,
    )

    # In fixed mode all workers can reach fetch_inventory().
    # In fault mode only the worker holding cache_lock can reach it.
    all_fetches_started.wait(timeout=2)

    with started_lock:
        concurrent_fetches = started_count

    # Always release workers before checking final results.
    release_fetch.set()

    for thread in threads:
        thread.join(timeout=2)

    blocked_threads = [
        thread.name
        for thread in threads
        if thread.is_alive()
    ]

    assert not blocked_threads, (
        "SCENARIO_ERROR[thread-contention]: "
        f"workers did not finish: {blocked_threads}"
    )

    assert not errors, (
        "SCENARIO_ERROR[thread-contention]: "
        f"worker exceptions: {errors}"
    )

    assert len(cache) == worker_count, (
        "SCENARIO_ERROR[thread-contention]: "
        f"expected {worker_count} results, got {len(cache)}"
    )

    assert concurrent_fetches == worker_count, (
        "FAULT_DETECTED[thread-contention]: "
        f"only {concurrent_fetches}/{worker_count} "
        "workers fetched concurrently"
    )
