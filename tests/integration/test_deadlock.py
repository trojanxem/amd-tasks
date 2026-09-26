"""Integration test for the circular-wait deadlock."""

from multiprocessing import Process
from pathlib import Path

import pytest

from amd_tasks.deadlock import start_inventory_sync


def _run_inventory_sync(
    inventory_path: str,
    sync_state_path: str,
    fault_enabled: bool,
) -> None:
    """Run the synchronization scenario inside a child process."""

    threads, completed = start_inventory_sync(
        Path(inventory_path),
        Path(sync_state_path),
        fault_enabled=fault_enabled,
    )

    for thread in threads:
        thread.join()

    incomplete_threads = [name for name, event in completed.items() if not event.is_set()]

    if incomplete_threads:
        raise RuntimeError(f"workers failed before completion: {incomplete_threads}")


def test_inventory_sync_completes(
    tmp_path,
    deadlock_fault: bool,
) -> None:
    """Inventory synchronization should finish without deadlocking."""

    inventory_file = tmp_path / "inventory.json"
    sync_state_file = tmp_path / "sync_state.txt"

    process = Process(
        target=_run_inventory_sync,
        args=(
            str(inventory_file),
            str(sync_state_file),
            deadlock_fault,
        ),
    )

    process.start()
    process.join(timeout=2)

    if process.is_alive():
        process.terminate()
        process.join(timeout=1)

        pytest.fail("FAULT_DETECTED[deadlock]: inventory synchronization exceeded watchdog timeout")

    assert process.exitcode == 0, (
        f"SCENARIO_ERROR[deadlock]: child process exited with code {process.exitcode}"
    )
