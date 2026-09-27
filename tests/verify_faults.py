"""Explicit CI check: each injected fault must fail its normal integration test.

Run with: python -m pytest -v tests/verify_faults.py
This filename intentionally keeps verification out of the default test run.
"""

import pytest

from tests.integration.test_cpu_contention import (
    test_foreground_request_gets_cpu_time as check_cpu,
)
from tests.integration.test_deadlock import test_inventory_sync_completes as check_deadlock
from tests.integration.test_io_contention import (
    test_storage_has_no_queueing_latency_spike as check_io,
)
from tests.integration.test_thread_contention import (
    test_inventory_fetches_run_concurrently as check_threads,
)
from tests.integration.test_toctou import test_disappearing_inventory_is_handled as check_toctou


@pytest.mark.parametrize(
    ("check", "args", "fault"),
    [
        (check_cpu, (True, 4), "cpu-contention"),
        (check_cpu, (True, 8), "cpu-contention"),
        (check_deadlock, (True,), "deadlock"),
        (check_io, (True, 4), "io-contention"),
        (check_io, (True, 8), "io-contention"),
        (check_threads, (True, 2), "thread-contention"),
        (check_threads, (True, 4), "thread-contention"),
    ],
)
def test_injected_fault_is_detected(check, args, fault):
    with pytest.raises(AssertionError, match=rf"FAULT_DETECTED\[{fault}\]"):
        check(*args)


def test_toctou_is_detected(tmp_path, monkeypatch):
    with pytest.raises(AssertionError, match=r"FAULT_DETECTED\[toctou\]"):
        check_toctou(tmp_path, monkeypatch, True)
