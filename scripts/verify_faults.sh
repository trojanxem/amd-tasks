#!/usr/bin/env bash

set -euo pipefail


expect_test_failure() {
    fault_name="$1"
    shift

    set +e
    "$@"
    status=$?
    set -e

    if [ "$status" -ne 1 ]; then
        echo "$fault_name was not detected correctly"
        echo "Expected pytest exit code: 1"
        echo "Actual exit code: $status"
        exit 1
    fi

    echo "$fault_name detected successfully"
}


expect_test_failure \
    "TOCTOU fault" \
    pytest -v tests/integration/test_toctou.py --race-fault

expect_test_failure \
    "Deadlock fault" \
    pytest -v tests/integration/test_deadlock.py --deadlock-fault
