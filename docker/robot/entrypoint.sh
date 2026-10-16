#!/usr/bin/env bash
set -eo pipefail

set +u
source /opt/ros/humble/setup.bash
set -u

api_port=${SURGINT_API_PORT:-7860}
api_base="http://127.0.0.1:${api_port}"
image_topic=${SURGINT_IMAGE_TOPIC:-/camera/image_raw}
result_topic=${SURGINT_RESULT_TOPIC:-/surgint/robot_results}
api_pid=""
bridge_pid=""

cleanup() {
    trap - EXIT INT TERM
    for pid in "$bridge_pid" "$api_pid"; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done
    for pid in "$bridge_pid" "$api_pid"; do
        if [ -n "$pid" ]; then
            wait "$pid" 2>/dev/null || true
        fi
    done
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

python -m uvicorn services.api.app:app \
    --host 0.0.0.0 \
    --port "$api_port" \
    --workers 1 &
api_pid=$!

ready=0
for _attempt in $(seq 1 120); do
    if python -c "import urllib.request; urllib.request.urlopen('${api_base}/health/ready', timeout=2)" 2>/dev/null; then
        ready=1
        break
    fi
    if ! kill -0 "$api_pid" 2>/dev/null; then
        wait "$api_pid"
        exit $?
    fi
    sleep 1
done

if [ "$ready" -ne 1 ]; then
    echo "SURGINT API did not become ready" >&2
    exit 1
fi

/usr/bin/python3 /app/bridge/ros/surgint_robot_bridge.py \
    --api-base "$api_base" \
    --image-topic "$image_topic" \
    --result-topic "$result_topic" &
bridge_pid=$!

set +e
wait -n "$api_pid" "$bridge_pid"
status=$?
set -e
exit "$status"
