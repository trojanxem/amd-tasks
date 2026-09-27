"""Integration test for the TOCTOU race condition."""

from pathlib import Path

from amd_tasks.race_condition import read_inventory, write_inventory
from tests.helpers import FaultDetected


def test_disappearing_inventory_is_handled(tmp_path, monkeypatch, race_fault: bool) -> None:
    inventory_file = tmp_path / "inventory.json"
    write_inventory(inventory_file)
    original_read_text = Path.read_text

    def remove_before_read(path, *args, **kwargs):
        if path == inventory_file:
            path.unlink()

        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", remove_before_read)

    try:
        result = read_inventory(inventory_file, fault_enabled=race_fault)
    except FileNotFoundError as error:
        print("TOCTOU: unhandled file disappearance")
        raise FaultDetected("toctou", "file disappeared before read") from error
    assert result is None
    print("TOCTOU: file disappearance handled")
