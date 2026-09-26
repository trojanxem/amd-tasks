"""CPU contention caused by unbounded compression workers."""

import gzip
import os
from multiprocessing import get_context


def _build_snapshot(
    switch_id: int,
    entry_count: int,
) -> bytes:
    """Build a realistic switch inventory snapshot."""

    lines = [
        (
            f"switch={switch_id},"
            f"mac=00:11:22:33:{entry // 256:02x}:{entry % 256:02x},"
            f"vlan={(entry % 4094) + 1},"
            f"port=Ethernet{entry % 48}\n"
        )
        for entry in range(entry_count)
    ]

    return "".join(lines).encode()


def _compress_snapshots(
    switch_ids: list[int],
    entry_count: int,
    result_queue,
) -> None:
    """Build and compress assigned switch snapshots."""

    for switch_id in switch_ids:
        snapshot = _build_snapshot(
            switch_id,
            entry_count,
        )

        compressed = gzip.compress(
            snapshot,
            compresslevel=9,
        )

        result_queue.put(
            (
                switch_id,
                len(compressed),
                os.getpid(),
            )
        )


def start_compression_jobs(
    fault_enabled: bool = False,
    snapshot_count: int = 8,
    worker_limit: int = 2,
    entry_count: int = 10_000,
):
    """Start CPU-bound inventory compression workers."""

    context = get_context("spawn")
    result_queue = context.Queue()

    switch_ids = list(range(snapshot_count))

    if fault_enabled:
        # BUG:
        # Start one CPU-bound process for every snapshot.
        work_groups = [[switch_id] for switch_id in switch_ids]
    else:
        # FIX:
        # Keep CPU concurrency bounded.
        worker_count = min(
            worker_limit,
            snapshot_count,
        )

        work_groups = [switch_ids[index::worker_count] for index in range(worker_count)]

    processes = [
        context.Process(
            target=_compress_snapshots,
            args=(
                work_group,
                entry_count,
                result_queue,
            ),
            name=f"compression-worker-{index}",
        )
        for index, work_group in enumerate(work_groups)
    ]

    for process in processes:
        process.start()

    return processes, result_queue
