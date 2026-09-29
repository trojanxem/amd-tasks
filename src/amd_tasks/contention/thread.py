"""Thread contention caused by a hot cache lock."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

Inventory = dict[str, object]


def start_inventory_workers(
    fetch_inventory: Callable[[int], Inventory],
    fault_enabled: bool = False,
    worker_count: int = 4,
):
    """Return (pool, jobs, cache); use `with pool` and read each job.result()."""
    pool = ThreadPoolExecutor(max_workers=worker_count)
    cache: dict[int, Inventory] = {}
    cache_lock = Lock()

    def worker(worker_id: int) -> None:
        if fault_enabled:
            # BUG: fetching holds the shared cache lock.
            with cache_lock:
                inventory = fetch_inventory(worker_id)
                cache[worker_id] = inventory
        else:
            # FIX: fetch before taking the lock to update the cache.
            inventory = fetch_inventory(worker_id)
            with cache_lock:
                cache[worker_id] = inventory

    jobs = [pool.submit(worker, worker_id) for worker_id in range(worker_count)]
    return pool, jobs, cache
