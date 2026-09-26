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

    parser.addoption(
        "--thread-contention-fault",
        action="store_true",
        default=False,
        help="Enable the thread contention fault",
    )

    parser.addoption(
        "--io-contention-fault",
        action="store_true",
        default=False,
        help="Enable the I/O contention fault",
    )

    parser.addoption(
        "--cpu-contention-fault",
        action="store_true",
        default=False,
        help="Enable the CPU contention fault",
    )


@pytest.fixture
def race_fault(request) -> bool:
    """Return whether the TOCTOU fault is enabled."""

    return request.config.getoption("--race-fault")


@pytest.fixture
def deadlock_fault(request) -> bool:
    """Return whether the deadlock fault is enabled."""

    return request.config.getoption("--deadlock-fault")


@pytest.fixture
def thread_contention_fault(request) -> bool:
    """Return whether the thread contention fault is enabled."""

    return request.config.getoption("--thread-contention-fault")


@pytest.fixture
def io_contention_fault(request) -> bool:
    """Return whether the I/O contention fault is enabled."""

    return request.config.getoption("--io-contention-fault")


@pytest.fixture
def cpu_contention_fault(request) -> bool:
    """Return whether the CPU contention fault is enabled."""

    return request.config.getoption("--cpu-contention-fault")
