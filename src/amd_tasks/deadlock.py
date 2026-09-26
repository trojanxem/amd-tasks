"""Circular-wait deadlock scenario."""

from pathlib import Path
from threading import Barrier, Event, Lock, Thread


def start_inventory_sync(
    inventory_path: Path,
    sync_state_path: Path,
    fault_enabled: bool = False,
) -> tuple[list[Thread], dict[str, Event]]:
    """Start inventory and sync-state updates."""

    inventory_path.write_text(
        '{"switch": "switch-1", "ports": 24}',
        encoding="utf-8",
    )

    inventory_lock = Lock()
    sync_state_lock = Lock()
    barrier = Barrier(2)

    inventory_done = Event()
    fetch_state_done = Event()

    def save_inventory() -> None:
        with inventory_lock:
            inventory_path.write_text(
                '{"switch": "switch-1", "ports": 48}',
                encoding="utf-8",
            )

            if fault_enabled:
                barrier.wait()

            with sync_state_lock:
                sync_state_path.write_text(
                    "inventory saved",
                    encoding="utf-8",
                )

        inventory_done.set()

    def update_fetch_state() -> None:
        if fault_enabled:
            # BUG:
            # Locks are acquired in the opposite order.
            with sync_state_lock:
                sync_state_path.write_text(
                    "inventory fetched",
                    encoding="utf-8",
                )

                barrier.wait()

                with inventory_lock:
                    inventory_path.read_text(
                        encoding="utf-8",
                    )

            fetch_state_done.set()
            return

        # FIX:
        # Both operations use the same lock order.
        with inventory_lock:
            with sync_state_lock:
                inventory_path.read_text(
                    encoding="utf-8",
                )

                sync_state_path.write_text(
                    "inventory fetched",
                    encoding="utf-8",
                )

        fetch_state_done.set()

    threads = [
        Thread(
            target=save_inventory,
            name="inventory-writer",
        ),
        Thread(
            target=update_fetch_state,
            name="fetch-state-writer",
        ),
    ]

    for thread in threads:
        thread.start()

    completed = {
        "inventory-writer": inventory_done,
        "fetch-state-writer": fetch_state_done,
    }

    return threads, completed
