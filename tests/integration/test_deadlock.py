"""Integration test for the circular-wait deadlock."""

from amd_tasks.deadlock import start_inventory_sync


def test_inventory_sync_completes(
    tmp_path,
    deadlock_fault: bool,
) -> None:
    """Inventory synchronization should finish successfully."""

    inventory_file = tmp_path / "inventory.json"
    sync_state_file = tmp_path / "sync_state.txt"

    threads, completed = start_inventory_sync(
        inventory_file,
        sync_state_file,
        fault_enabled=deadlock_fault,
    )

    # Watchdog: both threads must finish within the timeout.
    for thread in threads:
        thread.join(timeout=1)

    blocked_threads = [thread.name for thread in threads if thread.is_alive()]

    assert not blocked_threads, f"Deadlock detected: {blocked_threads}"

    incomplete_threads = [name for name, event in completed.items() if not event.is_set()]

    assert not incomplete_threads, f"Threads failed before completion: {incomplete_threads}"
