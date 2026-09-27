"""Check that isolation handles blocked workers and results larger than a pipe."""

from concurrent.futures import ThreadPoolExecutor
from multiprocessing import active_children
from threading import Event

import pytest

from tests.helpers import ScenarioError, run_isolated


def _blocked():
    Event().wait()


def _blocked_pool():
    pool = ThreadPoolExecutor(max_workers=1)
    pool.submit(Event().wait)
    return "worker still blocked after the scenario returned"


def _large_result():
    return b"x" * 1_000_000


def _broken():
    raise OSError("backend failed")


@pytest.mark.parametrize("function", [_blocked, _blocked_pool])
def test_watchdog_cleans_up_blocked_process(function):
    children_before = {child.pid for child in active_children()}
    with pytest.raises(ScenarioError, match="watchdog expired|blocked threads"):
        run_isolated(function, timeout=2)
    assert {child.pid for child in active_children()} == children_before


def test_large_result_does_not_block_shutdown():
    assert run_isolated(_large_result) == b"x" * 1_000_000


def test_worker_error_is_not_fault_detection():
    with pytest.raises(ScenarioError, match="backend failed"):
        run_isolated(_broken)
