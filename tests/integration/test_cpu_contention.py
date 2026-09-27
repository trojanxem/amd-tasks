"""A ready foreground request must get CPU time after at most one bulk chunk."""

import asyncio
import gzip

import pytest

from amd_tasks.contention.cpu import compress_inventory


def _scenario(fault_enabled, chunk_count):
    snapshots = [f"switch-{i}: ports=48\n".encode() * 1000 for i in range(chunk_count)]
    archives, response, delayed_by = asyncio.run(compress_inventory(snapshots, fault_enabled))
    assert [gzip.decompress(data) for data in archives] == snapshots
    assert gzip.decompress(response) == b"foreground inventory request"
    return delayed_by


@pytest.mark.parametrize("chunk_count", [4, 8])
def test_foreground_request_gets_cpu_time(cpu_contention_fault, chunk_count):
    delayed_by = _scenario(cpu_contention_fault, chunk_count)
    print(f"CPU: foreground waited for {delayed_by}/{chunk_count} bulk chunks; limit=1")
    assert delayed_by <= 1, (
        f"FAULT_DETECTED[cpu-contention]: foreground delayed by {delayed_by} chunks"
    )
