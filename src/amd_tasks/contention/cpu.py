"""CPU starvation: a bulk job monopolizes a shared event-loop thread."""

import asyncio
import gzip
from collections.abc import Callable


def compress_snapshot(snapshot: bytes) -> bytes:
    return gzip.compress(snapshot, compresslevel=9, mtime=0)


async def compress_inventory(
    snapshots: list[bytes],
    fault_enabled: bool = False,
    compress: Callable[[bytes], bytes] = compress_snapshot,
) -> tuple[list[bytes], bytes, int]:
    """Run bulk compression alongside a small, latency-sensitive CPU request.

    The returned count measures how many bulk chunks delay the foreground request.
    Both variants compress identical input; only scheduling differs.
    """
    if not snapshots:
        raise ValueError("at least one snapshot is required")
    archives: list[bytes] = []

    async def bulk() -> None:
        for snapshot in snapshots:
            archives.append(compress(snapshot))
            if not fault_enabled:
                # FIX: let other ready tasks use the shared CPU thread between chunks.
                await asyncio.sleep(0)
            # BUG: without the yield, the entire batch blocks the foreground task.

    async def foreground() -> tuple[bytes, int]:
        delayed_by = len(archives)
        return compress(b"foreground inventory request"), delayed_by

    # Schedule bulk first. Its first yield lets the waiting foreground task run.
    _, response = await asyncio.gather(bulk(), foreground())
    compressed_response, delayed_by = response
    return archives, compressed_response, delayed_by
