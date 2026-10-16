# verification

> records the current evidence for the robot runtime image.

**status:** verified locally, awaiting publication

## A. required evidence

- focused active-run discovery and bridge behavior tests;
- clean builds of the existing and robot image targets;
- service, ROS dependency, artifact, and non-root checks inside the robot image;
- local GPU and ROS replay smoke test;
- tray regression and relevant repository checks.

## B. recorded results

- `python -m ruff check bridge services surgint tests docker/robot/ros_smoke.py`: passed.
- `python -m pytest -q tests/unit`: 176 passed in 2.54 seconds.
- `python -m pytest -q tests/integration` with the three unavailable TestClient modules excluded: 92 passed in 2.50 seconds.
- `python -m pytest -q tests/model` in the CUDA environment with `motmetrics` supplied from the disposable test environment: 10 passed in 8.35 seconds.
- Shell syntax, workflow YAML parsing, and `git diff --check`: passed.
- The `robot-ci`, `robot-production`, and existing `ci` Docker targets built successfully. Both robot targets validated the packaged model manifest. The release build used model revision `bf22ea635858ec05edf272c8c27c36c05bc8f7ce`.
- The robot image ran as UID 1000, imported the installed service and ROS 2 Humble dependencies, and started one API worker plus the bridge without a runtime artifact download.
- The production robot image saw the local NVIDIA GeForce RTX 4090 through CUDA. A host ROS 2 Humble publisher sent `sensor_msgs/msg/Image` on `/camera/image_raw`; the bridge processed the frame through the active run and republished the unchanged response JSON as `std_msgs/msg/String` on `/surgint/robot_results`.
- Live checks covered no-active-run discovery, active-run attachment, frame processing, release, replacement-run discovery, clean container shutdown, and a `200` response from `/robot`.
- The existing tray image built and its session, frame, finalize, video, and release smoke checks passed on port 8002. The user's service on port 7860 was not touched.
- The `robot-v*` workflow builds and publishes only `ghcr.io/ahmedghita1/surgint-instruments-robot`; the existing `v*` publication path remains separate.

## C. limitations

The TestClient modules `test_api_health.py`, `test_api_robot_runs.py`, and `test_api_sessions.py` could not run on this workstation. The focused `test_api_robot_runs.py` attempt did not complete within 30 seconds, consistent with the existing local dependency limitation. The new active-run endpoint was instead exercised against both robot images, while registry and bridge behavior passed focused unit tests.

The ROS topics remain configurable defaults pending confirmation from the robot integration colleague. Jetson, ARM64, and robot-specific performance are outside this package. The GHCR image is not published until the user commits the checkpoint and pushes a `robot-v*` tag.
