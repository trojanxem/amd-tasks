"""Circular wait caused by inconsistent ordering of two locks."""

from pathlib import Path
from threading import Barrier, Event, Lock, Thread


def start_inventory_sync(
    inventory_path: Path,
    sync_state_path: Path,
    fault_enabled: bool = False,
) -> tuple[list[Thread], list[Event], Event]:
    """Start the two updates. Run the deadlock variant in a separate process."""
    inventory_path.write_text('{"switch": "switch-1", "ports": 24}', encoding="utf-8")
    inventory_lock = Lock()
    sync_state_lock = Lock()
    inventory_done = Event()
    fetch_state_done = Event()

    # The barrier sets this event only after both workers hold their first lock.
    both_locks_held = Event()
    barrier = Barrier(2, action=both_locks_held.set)

    def save_inventory() -> None:
        with inventory_lock:
            inventory_path.write_text('{"switch": "switch-1", "ports": 48}', encoding="utf-8")
            if fault_enabled:
                barrier.wait(timeout=5)
            with sync_state_lock:
                sync_state_path.write_text("inventory saved", encoding="utf-8")
        inventory_done.set()

    def update_fetch_state() -> None:
        if fault_enabled:
            # BUG: state first, inventory second -- the opposite of save_inventory().
            with sync_state_lock:
                barrier.wait(timeout=5)
                with inventory_lock:
                    inventory_path.read_text(encoding="utf-8")
                    sync_state_path.write_text("inventory fetched", encoding="utf-8")
        else:
            # FIX: inventory first, state second -- the same order in both workers.
            with inventory_lock:
                with sync_state_lock:
                    inventory_path.read_text(encoding="utf-8")
                    sync_state_path.write_text("inventory fetched", encoding="utf-8")
        fetch_state_done.set()

    # Daemon threads are confined to the scenario's subprocess.
    threads = [
        Thread(target=save_inventory, name="inventory-writer", daemon=True),
        Thread(target=update_fetch_state, name="fetch-state-writer", daemon=True),
    ]
    for thread in threads:
        thread.start()
    return threads, [inventory_done, fetch_state_done], both_locks_held
