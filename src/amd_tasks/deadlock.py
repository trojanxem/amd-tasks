"""Circular-wait deadlock scenario."""

from pathlib import Path
from threading import Barrier, Lock, Thread


def start_inventory_sync(
    inventory_path: Path,
    sync_state_path: Path,
    fault_enabled: bool = False,
) -> list[Thread]:
    """Start inventory and sync-state updates."""

    # Existing inventory from a previous switch fetch.
    inventory_path.write_text(
        '{"switch": "switch-1", "ports": 24}',
        encoding="utf-8",
    )

    inventory_lock = Lock()
    sync_state_lock = Lock()
    barrier = Barrier(2)

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

    def update_fetch_state() -> None:
        if fault_enabled:
            # BUG: opposite lock order.
            with sync_state_lock:
                sync_state_path.write_text(
                    "inventory fetched",
                    encoding="utf-8",
                )

                barrier.wait()

                with inventory_lock:
                    inventory_path.read_text(
                        encoding="utf-8"
                    )

            return

        # FIX: same lock order as save_inventory().
        with inventory_lock:
            with sync_state_lock:
                inventory_path.read_text(
                    encoding="utf-8"
                )

                sync_state_path.write_text(
                    "inventory fetched",
                    encoding="utf-8",
                )

    threads = [
        Thread(
            target=save_inventory,
            name="inventory-writer",
            daemon=True,
        ),
        Thread(
            target=update_fetch_state,
            name="fetch-state-writer",
            daemon=True,
        ),
    ]

    for thread in threads:
        thread.start()

    return threads
