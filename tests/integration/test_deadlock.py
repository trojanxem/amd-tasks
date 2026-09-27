"""Bounded observation of the two-lock circular wait."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic

from amd_tasks.deadlock import start_inventory_sync
from tests.helpers import FaultDetected, ScenarioError, run_isolated


def _scenario(fault_enabled):
    with TemporaryDirectory() as directory:
        inventory, state = Path(directory) / "inventory.json", Path(directory) / "state.txt"
        threads, waiting, errors = start_inventory_sync(inventory, state, fault_enabled)
        deadline = monotonic() + 2
        for thread in threads:
            thread.join(max(0, deadline - monotonic()))
        if errors:
            raise ScenarioError(f"inventory worker failed: {errors}")
        if all(event.is_set() for event in waiting):
            # Each thread holds one different lock while requesting the other's.
            return True
        if any(thread.is_alive() for thread in threads):
            raise ScenarioError("workers stalled without evidence of circular wait")
        assert json.loads(inventory.read_text()) == {"switch": "switch-1", "ports": 48}
        assert state.read_text() == "inventory synchronized"
        return False


def test_inventory_sync_completes(deadlock_fault):
    circular_wait = run_isolated(_scenario, deadlock_fault)
    print(f"Deadlock: circular_wait={circular_wait}")
    if circular_wait:
        raise FaultDetected("deadlock", "both workers hold one lock and wait for the other")
