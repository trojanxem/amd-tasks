"""I/O contention caused by excessive synchronous disk flushes."""

import json
import os
from pathlib import Path
from threading import Barrier, Lock, Thread


def start_snapshot_writers(
    output_dir: Path,
    fault_enabled: bool = False,
    switch_count: int = 4,
    ports_per_switch: int = 8,
) -> tuple[list[Thread], list[tuple[int, Exception]]]:
    """Start concurrent inventory snapshot writers."""

    output_dir.mkdir(parents=True, exist_ok=True)

    start_barrier = Barrier(switch_count)

    errors = []
    errors_lock = Lock()

    def write_snapshot(switch_id: int) -> None:
        try:
            ports = [
                {
                    "port": port,
                    "status": "up",
                }
                for port in range(ports_per_switch)
            ]

            snapshot_file = output_dir / f"switch-{switch_id}.jsonl"

            # Start disk operations at roughly the same time.
            start_barrier.wait()

            with snapshot_file.open(
                "w",
                encoding="utf-8",
            ) as file:
                if fault_enabled:
                    # BUG:
                    # Every small write is synchronously flushed
                    # to disk, causing excessive I/O pressure.
                    for port in ports:
                        file.write(json.dumps(port) + "\n")
                        file.flush()
                        os.fsync(file.fileno())

                    return

                # FIX:
                # Batch the snapshot and flush it once.
                payload = "".join(json.dumps(port) + "\n" for port in ports)

                file.write(payload)
                file.flush()
                os.fsync(file.fileno())

        except Exception as error:
            with errors_lock:
                errors.append((switch_id, error))

    threads = [
        Thread(
            target=write_snapshot,
            args=(switch_id,),
            name=f"snapshot-writer-{switch_id}",
        )
        for switch_id in range(switch_count)
    ]

    for thread in threads:
        thread.start()

    return threads, errors
