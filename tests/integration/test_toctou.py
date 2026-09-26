"""Integration test for the TOCTOU race condition."""

from pathlib import Path

import pytest

from amd_tasks.race_condition import read_inventory, write_inventory


def test_disappearing_inventory_is_handled(
    tmp_path,
    monkeypatch,
    race_fault: bool,
) -> None:
    """Inventory disappearing before read should be handled safely."""

    inventory_file = tmp_path / "inventory.json"

    write_inventory(inventory_file)

    original_read_text = Path.read_text

    def remove_before_read(path, *args, **kwargs):
        path.unlink()

        return original_read_text(
            path,
            *args,
            **kwargs,
        )

    monkeypatch.setattr(
        Path,
        "read_text",
        remove_before_read,
    )

    try:
        result = read_inventory(
            inventory_file,
            fault_enabled=race_fault,
        )
    except FileNotFoundError:
        pytest.fail("FAULT_DETECTED[toctou]: file disappeared between existence check and read")

    assert result is None
