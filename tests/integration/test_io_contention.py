"""Measure I/O queueing latency against a controlled service time."""

import json
from pathlib import Path
from queue import Queue
from tempfile import TemporaryDirectory
from threading import BoundedSemaphore, Event, Lock
from time import monotonic, sleep

import pytest

from amd_tasks.contention.io import persist_snapshot, start_snapshot_writers

SERVICE_TIME = 0.02  # Model a storage/network request taking at least 20 ms.


def _measure_storage_wait(fault_enabled, switch_count):
    capacity = 2
    slots = BoundedSemaphore(capacity)
    requests_started: Queue[None] = Queue()
    release = Event()
    waits_lock = Lock()
    waits: list[float] = []

    def persist(path, payload):
        started = monotonic()
        acquired = slots.acquire(blocking=False)
        requests_started.put(None)
        if not acquired:
            # Measure real blocking on an occupied slot, not the file write itself.
            slots.acquire()
            waited = monotonic() - started
            with waits_lock:
                waits.append(waited)
        try:
            # Hold occupied slots until all clients have attempted access.
            release.wait()
            sleep(SERVICE_TIME)
            persist_snapshot(path, payload)
        finally:
            slots.release()

    with TemporaryDirectory() as directory:
        root = Path(directory)
        pool, jobs = start_snapshot_writers(
            root, fault_enabled, switch_count, io_limit=capacity, persist=persist
        )
        with pool:
            try:
                # Each worker reports its first request before any write can finish.
                for _ in jobs:
                    requests_started.get(timeout=5)
            finally:
                release.set()
            for job in jobs:
                job.result()
        assert {path.name for path in root.iterdir()} == {
            f"switch-{i}.jsonl" for i in range(switch_count)
        }
        for path in root.iterdir():
            assert [json.loads(line) for line in path.read_text().splitlines()] == [
                {"port": i, "status": "up"} for i in range(8)
            ]
    return len(waits), max(waits, default=0.0)


@pytest.mark.parametrize("switch_count", [4, 8])
def test_storage_has_no_queueing_latency_spike(io_contention_fault, switch_count):
    queued, max_wait = _measure_storage_wait(io_contention_fault, switch_count)
    print(
        f"I/O: {queued} queued requests; max slot wait={max_wait * 1000:.1f} ms; "
        f"service time >= {SERVICE_TIME * 1000:.0f} ms"
    )
    assert max_wait < SERVICE_TIME, (
        f"FAULT_DETECTED[io-contention]: slot wait {max_wait * 1000:.1f} ms "
        f">= one service interval; {queued} queued requests"
    )
