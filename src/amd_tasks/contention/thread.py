"""Thread contention caused by a hot cache lock."""

from threading import Lock, Thread


def start_inventory_workers(
    fetch_inventory,
    fault_enabled: bool = False,
    worker_count: int = 4,
) -> tuple[
    list[Thread],
    dict[int, dict],
    list[tuple[int, Exception]],
]:
    """Start concurrent inventory workers."""

    cache = {}
    errors = []

    cache_lock = Lock()
    errors_lock = Lock()

    def worker(worker_id: int) -> None:
        try:
            if fault_enabled:
                # BUG:
                # The shared cache lock is held during the fetch.
                with cache_lock:
                    inventory = fetch_inventory(worker_id)
                    cache[worker_id] = inventory

                return

            # FIX:
            # Expensive work happens outside the critical section.
            inventory = fetch_inventory(worker_id)

            with cache_lock:
                cache[worker_id] = inventory

        except Exception as error:
            with errors_lock:
                errors.append((worker_id, error))

    threads = [
        Thread(
            target=worker,
            args=(worker_id,),
            name=f"inventory-worker-{worker_id}",
            daemon=True,
        )
        for worker_id in range(worker_count)
    ]

    for thread in threads:
        thread.start()

    return threads, cache, errors
