# implementation plan

**status:** implemented

**branch:** `feat/robot-deploy`

## A. foundation

The robot workflow API, operator page, ROS 2 bridge, pinned release-model build, and existing tray-service image already exist. The new image packages those pieces without changing their domain contracts.

## B. approach

### B.1 dedicated robot runtime image

- Add active-run discovery for the bridge while retaining explicit run IDs for standalone use.
- Add a ROS 2 Humble image target and a small launcher for the API and bridge.
- Add a separate `robot-v*` GHCR publication path and robot pull-and-run instructions.
- Verify focused behavior, both image targets, local GPU startup, ROS replay, and tray regressions.
- **commit:** `build: add robot runtime image`

## C. affected boundaries

- `bridge/ros`: active-run discovery and no-run skip behavior;
- `services/api`: read-only discovery of the current non-terminal robot run;
- `Dockerfile`, `.dockerignore`, `docker/robot`, and `.github/workflows/ci.yml`: robot build, startup, smoke test, and publication;
- focused API and bridge tests;
- this feature package's verification record.

## D. escalation conditions

- the image requires ROS dependencies in the SURGINT package;
- the robot computer is not x86-64 or cannot run CUDA 12.1 containers;
- one-container startup requires changing robot result meaning, lifecycle, or the one-active-run constraint;
- ROS 2 cannot communicate through host networking and IPC on the target computer.
