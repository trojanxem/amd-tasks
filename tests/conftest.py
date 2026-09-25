import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--race-fault",
        action="store_true",
        default=False,
        help="Enable race condition fault",
    )


@pytest.fixture
def race_fault(request) -> bool:
    return request.config.getoption("--race-fault")
