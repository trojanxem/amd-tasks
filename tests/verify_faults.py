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


@pytest.mark.parametrize("chunk_count", [4, 8])
def test_cpu_fault_is_detected(chunk_count):
    with pytest.raises(AssertionError, match=r"FAULT_DETECTED\[cpu-contention\]"):
        check_cpu(cpu_contention_fault=True, chunk_count=chunk_count)


def test_deadlock_is_detected():
    with pytest.raises(AssertionError, match=r"FAULT_DETECTED\[deadlock\]"):
        check_deadlock(deadlock_fault=True)


@pytest.mark.parametrize("switch_count", [4, 8])
def test_io_fault_is_detected(switch_count):
    with pytest.raises(AssertionError, match=r"FAULT_DETECTED\[io-contention\]"):
        check_io(io_contention_fault=True, switch_count=switch_count)


@pytest.mark.parametrize("worker_count", [2, 4])
def test_thread_fault_is_detected(worker_count):
    with pytest.raises(AssertionError, match=r"FAULT_DETECTED\[thread-contention\]"):
        check_threads(thread_contention_fault=True, worker_count=worker_count)


def test_toctou_is_detected(tmp_path, monkeypatch):
    with pytest.raises(AssertionError, match=r"FAULT_DETECTED\[toctou\]"):
        check_toctou(tmp_path, monkeypatch, race_fault=True)
