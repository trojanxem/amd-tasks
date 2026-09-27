"""Portable process isolation and worker cleanup for concurrency tests."""

import traceback
from multiprocessing import get_context
from time import monotonic


class FaultDetected(AssertionError):
    """A detector observed the intended defect."""

    def __init__(self, fault: str, detail: str) -> None:
        self.fault = fault
        super().__init__(f"FAULT_DETECTED[{fault}]: {detail}")


class ScenarioError(RuntimeError):
    """The scenario failed; this does not count as fault detection."""


def _child(connection, function, args, kwargs):
    try:
        connection.send((True, function(*args, **kwargs)))
    except Exception:
        connection.send((False, traceback.format_exc()))
    finally:
        connection.close()


def run_isolated(function, *args, timeout: float = 15, **kwargs):
    """Run a thread/async scenario in one spawned process, on any supported OS.

    The target must be importable (a module-level function). It may create threads,
    but not child processes. Receive results before joining to avoid a full pipe.
    """
    context = get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_child, args=(sender, function, args, kwargs), daemon=True)
    deadline = monotonic() + timeout
    try:
        process.start()
        sender.close()
        if not receiver.poll(max(0, deadline - monotonic())):
            raise ScenarioError("scenario watchdog expired")
        try:
            success, result = receiver.recv()
        except EOFError as error:
            raise ScenarioError("scenario exited without a result") from error
        if not success:
            raise ScenarioError(result)
        process.join(max(0, deadline - monotonic()))
        if process.is_alive():
            raise ScenarioError("scenario left blocked threads behind")
        if process.exitcode != 0:
            raise ScenarioError(f"scenario exited with code {process.exitcode}")
        return result
    finally:
        if process.pid is not None:
            if process.is_alive():
                process.terminate()
                process.join(timeout=2)
            if process.is_alive():
                process.kill()
            process.join(timeout=2)
            process.close()
        sender.close()
        receiver.close()
