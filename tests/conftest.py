"""Shared pytest configuration."""

import pytest


def pytest_addoption(parser) -> None:
    """Add fault injection options."""

    parser.addoption(
        "--race-fault",
        action="store_true",
        default=False,
        help="Enable the TOCTOU race fault",
    )

    parser.addoption(
        "--deadlock-fault",
        action="store_true",
        default=False,
        help="Enable the circular-wait deadlock fault",
    )


@pytest.fixture
def race_fault(request) -> bool:
    """Return whether the TOCTOU race fault is enabled."""

    return request.config.getoption("--race-fault")


@pytest.fixture
def deadlock_fault(request) -> bool:
    """Return whether the deadlock fault is enabled."""

    return request.config.getoption("--deadlock-fault")
