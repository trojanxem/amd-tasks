"""Shared pytest configuration."""

import pytest


def pytest_addoption(parser) -> None:
    """Add fault injection command-line options."""

    parser.addoption(
        "--race-fault",
        action="store_true",
        default=False,
        help="Enable the TOCTOU race fault",
    )


@pytest.fixture
def race_fault(request) -> bool:
    """Return whether the TOCTOU fault is enabled."""

    return request.config.getoption("--race-fault")
