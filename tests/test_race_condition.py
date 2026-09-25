from amd_tasks.race_condition import collect_inventory


def test_inventory_collection(race_fault: bool) -> None:
    result = collect_inventory(fault_enabled=race_fault)
    assert set(result) == {"node-a", "node-b"}
