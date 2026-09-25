"""Unit tests for inventory file access."""

from amd_tasks.race_condition import read_inventory, write_inventory


def test_write_inventory_creates_file(tmp_path) -> None:
    """Inventory writer should create the inventory file."""

    inventory_file = tmp_path / "inventory.json"

    write_inventory(inventory_file)

    assert inventory_file.exists()


def test_read_inventory(tmp_path) -> None:
    """Existing inventory should be read successfully."""

    inventory_file = tmp_path / "inventory.json"

    write_inventory(inventory_file)

    result = read_inventory(inventory_file)

    assert result == {
        "switch": "switch-1",
        "ports": 48,
    }


def test_missing_inventory_returns_none(tmp_path) -> None:
    """Missing inventory should not crash the reader."""

    inventory_file = tmp_path / "inventory.json"

    result = read_inventory(inventory_file)

    assert result is None
