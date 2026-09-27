"""Shared pytest configuration."""

import pytest


def pytest_addoption(parser) -> None:
    """Add fault injection options."""

    for name, description in [
        ("race", "TOCTOU race"),
        ("deadlock", "circular-wait deadlock"),
        ("thread-contention", "hot cache lock"),
        ("io-contention", "excess I/O writers"),
        ("cpu-contention", "CPU starvation"),
    ]:
        parser.addoption(
            f"--{name}-fault", action="store_true", default=False, help=f"Enable {description}"
        )


@pytest.fixture
def race_fault(request) -> bool:
    return request.config.getoption("--race-fault")


@pytest.fixture
def deadlock_fault(request) -> bool:
    return request.config.getoption("--deadlock-fault")


@pytest.fixture
def thread_contention_fault(request) -> bool:
    return request.config.getoption("--thread-contention-fault")


@pytest.fixture
def io_contention_fault(request) -> bool:
    return request.config.getoption("--io-contention-fault")


@pytest.fixture
def cpu_contention_fault(request) -> bool:
    return request.config.getoption("--cpu-contention-fault")
