"""Bounded observation of the two-lock circular wait."""

import json
from multiprocessing import get_context
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic

from amd_tasks.deadlock import start_inventory_sync


def _run_inventory_sync(fault_enabled, circular_wait):
    with TemporaryDirectory() as directory:
        inventory, state = Path(directory) / "inventory.json", Path(directory) / "state.txt"
        threads, completed, both_locks_held = start_inventory_sync(inventory, state, fault_enabled)
        deadline = monotonic() + 2
        for thread in threads:
            thread.join(max(0, deadline - monotonic()))
        if both_locks_held.is_set() and all(thread.is_alive() for thread in threads):
            # Both passed the barrier holding different locks; neither can get the other.
            circular_wait.set()
            return
        assert not any(thread.is_alive() for thread in threads), (
            "workers stalled without evidence of circular wait"
        )
        assert all(event.is_set() for event in completed), "a worker failed before completion"
        assert json.loads(inventory.read_text()) == {"switch": "switch-1", "ports": 48}
        assert state.read_text() in {"inventory saved", "inventory fetched"}


def test_inventory_sync_completes(deadlock_fault):
    # Only this scenario intentionally leaves blocked threads behind.
    context = get_context("spawn")
    circular_wait = context.Event()
    process = context.Process(target=_run_inventory_sync, args=(deadlock_fault, circular_wait))
    process.start()
    try:
        process.join(timeout=15)
        assert not process.is_alive(), "deadlock scenario did not finish in 15 seconds"
        assert process.exitcode == 0, "deadlock scenario failed; see the child traceback"
    finally:
        if process.is_alive():
            process.terminate()
        process.join()
        process.close()
    print(f"Deadlock: circular_wait={circular_wait.is_set()}")
    assert not circular_wait.is_set(), (
        "FAULT_DETECTED[deadlock]: both workers hold one lock and wait for the other"
    )
