#!/usr/bin/env bash

set -euo pipefail


expect_fault() {
    fault_name="$1"
    expected_marker="$2"
    shift 2

    output_file="$(mktemp)"

    set +e
    "$@" 2>&1 | tee "$output_file"
    status=${PIPESTATUS[0]}
    set -e

    if [ "$status" -ne 1 ]; then
        echo "$fault_name was not detected correctly"
        echo "Expected pytest exit code: 1"
        echo "Actual exit code: $status"
        rm -f "$output_file"
        exit 1
    fi

    if ! grep -Fq "$expected_marker" "$output_file"; then
        echo "$fault_name test failed, but not because the expected fault was detected"
        echo "Expected marker: $expected_marker"
        rm -f "$output_file"
        exit 1
    fi

    rm -f "$output_file"

    echo "$fault_name detected successfully"
}


expect_fault \
    "TOCTOU fault" \
    "FAULT_DETECTED[toctou]" \
    pytest -v tests/integration/test_toctou.py --race-fault

expect_fault \
    "Deadlock fault" \
    "FAULT_DETECTED[deadlock]" \
    pytest -v tests/integration/test_deadlock.py --deadlock-fault

expect_fault \
    "Thread contention fault" \
    "FAULT_DETECTED[thread-contention]" \
    pytest -v tests/integration/test_thread_contention.py --thread-contention-fault
