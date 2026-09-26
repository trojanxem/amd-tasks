"""Integration test for I/O contention."""

import os
from threading import Lock
from time import perf_counter

from amd_tasks.contention.io import start_snapshot_writers


def test_inventory_snapshots_use_batched_io(
    tmp_path,
    monkeypatch,
    io_contention_fault: bool,
) -> None:
    """Inventory snapshots should avoid excessive disk flushes."""

    switch_count = 4
    ports_per_switch = 8

    fsync_count = 0
    fsync_lock = Lock()

    original_fsync = os.fsync

    def measured_fsync(fd) -> None:
        nonlocal fsync_count

        with fsync_lock:
            fsync_count += 1

        # Perform the real disk sync.
        original_fsync(fd)

    monkeypatch.setattr(
        os,
        "fsync",
        measured_fsync,
    )

    start = perf_counter()

    threads, errors = start_snapshot_writers(
        output_dir=tmp_path,
        fault_enabled=io_contention_fault,
        switch_count=switch_count,
        ports_per_switch=ports_per_switch,
    )

    for thread in threads:
        thread.join(timeout=5)

    duration = perf_counter() - start

    blocked_threads = [thread.name for thread in threads if thread.is_alive()]

    assert not blocked_threads, (
        f"SCENARIO_ERROR[io-contention]: workers did not finish: {blocked_threads}"
    )

    assert not errors, f"SCENARIO_ERROR[io-contention]: worker exceptions: {errors}"

    snapshot_files = list(tmp_path.glob("switch-*.jsonl"))

    assert len(snapshot_files) == switch_count, (
        "SCENARIO_ERROR[io-contention]: "
        f"expected {switch_count} snapshots, "
        f"got {len(snapshot_files)}"
    )

    for snapshot_file in snapshot_files:
        lines = snapshot_file.read_text(encoding="utf-8").splitlines()

        assert len(lines) == ports_per_switch, (
            f"SCENARIO_ERROR[io-contention]: incomplete snapshot: {snapshot_file.name}"
        )

    print(f"I/O metrics: fsync={fsync_count}, duration={duration:.4f}s")

    expected_fsync_count = switch_count

    assert fsync_count == expected_fsync_count, (
        "FAULT_DETECTED[io-contention]: "
        f"{fsync_count} synchronous disk flushes, "
        f"expected {expected_fsync_count}"
    )
