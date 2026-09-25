from threading import Event, Thread


def collect_inventory(fault_enabled: bool = False) -> dict:
    """Collect switch inventory from two nodes."""

    results = {}

    release_node_b = Event()
    # This makes the race deterministic instead of relying on sleep

    def node_a() -> None:
        results["node-a"] = {"ports": 48}

    def node_b() -> None:
        release_node_b.wait()
        results["node-b"] = {"ports": 64}

    thread_node_a = Thread(target=node_a)
    thread_node_b = Thread(target=node_b)

    thread_node_a.start()
    thread_node_b.start()

    thread_node_a.join()

    if fault_enabled:
        # BUG, let's aggregate results before B has finished

        snapshot = results.copy()

        release_node_b.set()
        thread_node_b.join()

        return snapshot

    release_node_b.set()
    thread_node_b.join()

    return results.copy()
