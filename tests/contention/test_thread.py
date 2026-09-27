"""Regression coverage for worker exceptions and invalid inputs."""

import pytest

from amd_tasks.contention.thread import start_inventory_workers


def test_fetch_exception_is_not_a_successful_run():
    def fail(worker_id):
        raise OSError("fetch unavailable")

    pool, jobs, cache = start_inventory_workers(fail)
    with pool:
        for job in jobs:
            with pytest.raises(OSError, match="fetch unavailable"):
                job.result()
    assert not cache


@pytest.mark.parametrize("workers", [0, -1])
def test_invalid_worker_count(workers):
    with pytest.raises(ValueError):
        start_inventory_workers(lambda index: {}, worker_count=workers)
