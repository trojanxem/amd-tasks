"""Check persistence contracts and reject corruption independently of contention."""

import json
from time import sleep

import pytest

from amd_tasks.contention.io import start_snapshot_writers
from tests.integration import test_io_contention


def test_complete_valid_snapshots(tmp_path):
    pool, jobs = start_snapshot_writers(tmp_path, switch_count=3, ports_per_switch=5)
    with pool:
        for job in jobs:
            job.result()
    assert {path.name for path in tmp_path.iterdir()} == {f"switch-{i}.jsonl" for i in range(3)}
    for path in tmp_path.iterdir():
        assert [json.loads(line) for line in path.read_text().splitlines()] == [
            {"port": i, "status": "up"} for i in range(5)
        ]


def test_persist_failure_is_not_contention(tmp_path):
    def fail(path, payload):
        raise OSError("storage unavailable")

    pool, jobs = start_snapshot_writers(tmp_path, persist=fail)
    with pool:
        for job in jobs:
            with pytest.raises(OSError, match="storage unavailable"):
                job.result()


def test_invalid_json_is_rejected(monkeypatch):
    def corrupt(path, payload):
        path.write_text("BROKEN_NOT_JSON\n" * 8)

    monkeypatch.setattr(test_io_contention, "persist_snapshot", corrupt)
    with pytest.raises(json.JSONDecodeError):
        test_io_contention._scenario(False, 4)


def test_slow_writes_without_queueing_are_not_contention(monkeypatch):
    persist = test_io_contention.persist_snapshot

    def slow_write(path, payload):
        sleep(2 * test_io_contention.SERVICE_TIME)
        persist(path, payload)

    monkeypatch.setattr(test_io_contention, "persist_snapshot", slow_write)
    queued, max_wait = test_io_contention._scenario(False, 4)
    assert queued == 0
    assert max_wait == 0
