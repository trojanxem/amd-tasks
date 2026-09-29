"""I/O contention caused by ignoring a storage service's concurrency budget."""

import json
import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

Persist = Callable[[Path, str], None]


def persist_snapshot(path: Path, payload: str) -> None:
    """Persist one complete snapshot, synchronizing once per snapshot."""
    with path.open("w", encoding="utf-8") as file:
        file.write(payload)
        file.flush()
        os.fsync(file.fileno())


def start_snapshot_writers(
    output_dir: Path,
    fault_enabled: bool = False,
    switch_count: int = 4,
    ports_per_switch: int = 8,
    io_limit: int = 2,
    persist: Persist = persist_snapshot,
):
    """Return (pool, jobs); use `with pool` and read each job.result()."""
    if min(switch_count, ports_per_switch, io_limit) < 1:
        raise ValueError("counts and io_limit must be positive")
    output_dir.mkdir(parents=True, exist_ok=True)
    if fault_enabled:
        # BUG: one writer per item disregards the storage service's I/O budget.
        worker_count = switch_count
    else:
        # FIX: keep the number of writers within the service's capacity.
        worker_count = min(io_limit, switch_count)

    def write_snapshots(worker_id: int) -> None:
        # With two workers: worker 0 writes switches 0, 2, ...; worker 1 writes 1, 3, ...
        for switch_id in range(worker_id, switch_count, worker_count):
            records = [{"port": port, "status": "up"} for port in range(ports_per_switch)]
            payload = "".join(json.dumps(record) + "\n" for record in records)
            persist(output_dir / f"switch-{switch_id}.jsonl", payload)

    pool = ThreadPoolExecutor(max_workers=worker_count)
    jobs = [pool.submit(write_snapshots, index) for index in range(worker_count)]
    return pool, jobs
