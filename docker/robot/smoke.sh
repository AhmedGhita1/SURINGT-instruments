#!/usr/bin/env bash
set -u

BASE=${BASE:-http://127.0.0.1:8001}
PYTHON=${PYTHON:-python3}
failures=0

expect() {
    printf '%-30s %s\n' "$1" "$2"
    if [ "$2" != "$3" ]; then
        echo "  expected $3"
        failures=$((failures + 1))
    fi
}

status() { curl -s -o /dev/null -w '%{http_code}' -m "$1" "${@:2}"; }

expect "GET /health/ready" "$(status 10 "$BASE/health/ready")" 200
expect "GET active before run" "$(status 10 "$BASE/v1/robot-runs/active")" 404

started=$(curl -sS -m 30 -X POST \
    -H 'Content-Type: application/json' \
    -d '{"workflow_stage":"post-procedure-clearing","contamination_state":"not-regulated","lifecycle":"reusable"}' \
    "$BASE/v1/robot-runs")
run_id=$(printf '%s' "$started" | "$PYTHON" -c 'import json,sys; print(json.load(sys.stdin)["status"]["run_id"])')

active=$(curl -sS -m 10 "$BASE/v1/robot-runs/active" \
    | "$PYTHON" -c 'import json,sys; print(json.load(sys.stdin)["status"]["run_id"])')
expect "GET active run" "$active" "$run_id"

expect "POST stop" "$(status 30 -X POST "$BASE/v1/robot-runs/$run_id/stop")" 200
expect "GET active after stop" "$(status 10 "$BASE/v1/robot-runs/active")" 404
expect "DELETE run" "$(status 30 -X DELETE "$BASE/v1/robot-runs/$run_id")" 204

if [ "$failures" -ne 0 ]; then
    echo "$failures check(s) failed"
    exit 1
fi
echo "all robot checks passed"
