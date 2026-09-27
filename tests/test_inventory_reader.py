"""Unit tests for inventory file access."""

from amd_tasks.race_condition import read_inventory, write_inventory


def test_write_inventory_creates_file(tmp_path) -> None:
    inventory_file = tmp_path / "inventory.json"
    write_inventory(inventory_file)
    assert inventory_file.exists()


def test_read_inventory(tmp_path) -> None:
    inventory_file = tmp_path / "inventory.json"
    write_inventory(inventory_file)
    assert read_inventory(inventory_file) == {"switch": "switch-1", "ports": 48}


def test_missing_inventory_returns_none(tmp_path) -> None:
    inventory_file = tmp_path / "inventory.json"
    assert read_inventory(inventory_file) is None
