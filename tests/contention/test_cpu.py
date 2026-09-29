"""Invalid input, compression failures, and corruption must fail normally."""

import asyncio
import gzip

import pytest

from amd_tasks.contention.cpu import compress_inventory
from tests.integration import test_cpu_contention


def test_empty_batch_is_rejected():
    with pytest.raises(ValueError):
        asyncio.run(compress_inventory([]))


def test_compression_failure_is_not_contention():
    def fail(snapshot):
        raise OSError("compression unavailable")

    with pytest.raises(OSError, match="compression unavailable"):
        asyncio.run(compress_inventory([b"inventory"], compress=fail))


def test_invalid_compressed_payload_is_rejected(monkeypatch):
    async def corrupt(snapshots, fault_enabled):
        return [b"bad"] * len(snapshots), b"bad", 1

    monkeypatch.setattr(test_cpu_contention, "compress_inventory", corrupt)
    with pytest.raises(gzip.BadGzipFile):
        test_cpu_contention.test_foreground_request_gets_cpu_time(False, 4)
