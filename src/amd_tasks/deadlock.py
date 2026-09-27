"""Circular wait caused by inconsistent ordering of two locks."""

from pathlib import Path
from threading import Barrier, Event, Lock, Thread


def start_inventory_sync(inventory_path: Path, state_path: Path, fault_enabled: bool = False):
    """Start two updates; run this deliberately unsafe example in an isolated process.

    Each waiting event is set while its worker holds the first lock and requests
    the second. In the faulty order, both events being set proves the two-lock cycle.
    """
    inventory_path.write_text('{"switch": "switch-1", "ports": 24}', encoding="utf-8")
    inventory_lock, state_lock = Lock(), Lock()
    barrier = Barrier(2)
    waiting = [Event(), Event()]
    errors: list[tuple[int, Exception]] = []
    error_lock = Lock()

    def update(worker_id: int) -> None:
        first, second = inventory_lock, state_lock
        if fault_enabled and worker_id == 1:
            first, second = state_lock, inventory_lock
        try:
            with first:
                if fault_enabled:
                    barrier.wait(timeout=5)
                waiting[worker_id].set()
                with second:
                    waiting[worker_id].clear()
                    if worker_id == 0:
                        inventory_path.write_text(
                            '{"switch": "switch-1", "ports": 48}', encoding="utf-8"
                        )
                    else:
                        inventory_path.read_text(encoding="utf-8")
                    state_path.write_text("inventory synchronized", encoding="utf-8")
        except Exception as error:
            with error_lock:
                errors.append((worker_id, error))

    # Daemon threads are confined to the scenario's subprocess.
    threads = [Thread(target=update, args=(i,), daemon=True) for i in range(2)]
    for thread in threads:
        thread.start()
    return threads, waiting, errors
