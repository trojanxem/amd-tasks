"""TOCTOU race condition for inventory file access."""

import json
from pathlib import Path


def write_inventory(path: Path) -> None:
    """Write sample switch inventory to a file."""

    inventory = {
        "switch": "switch-1",
        "ports": 48,
    }

    path.write_text(
        json.dumps(inventory),
        encoding="utf-8",
    )


def read_inventory(
    path: Path,
    fault_enabled: bool = False,
) -> dict | None:
    """Read switch inventory from a file."""

    if fault_enabled:
        # BUG:
        # The file may disappear between the existence check
        # and the actual read.
        if not path.exists():
            return None

        return json.loads(path.read_text(encoding="utf-8"))

    # FIX:
    # Do not rely on a previous existence check.
    # Try to read the file and handle its disappearance.
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
