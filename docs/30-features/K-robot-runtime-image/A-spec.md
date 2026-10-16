# feature package: robot runtime image

> defines a separate self-contained container image for the ROS 2 robot workflow.

**status:** approved

**roadmap relationship:** packages the R4 robot workflow for an x86-64 Linux computer with an NVIDIA GPU.

## A. outcome

A robot operator can pull and run a dedicated SURGINT robot image that starts the shared CUDA runtime and ROS 2 Humble bridge together, without changing the existing tray-service image.

## B. sub-features

### B.1 RDI-01: separate robot image

**definition:** Packages the robot workflow as a distinct GHCR image.

**specification:**

- Build `ghcr.io/ahmedghita1/surgint-instruments-robot` separately from the existing `surgint-instruments` image.
- Bake the same pinned model and application release into the robot image.
- Include ROS 2 Humble and the bridge without adding ROS dependencies to the SURGINT Python package.

**verification:** A clean build validates the model artifact, imports the installed service package, and imports the ROS bridge dependencies.

### B.2 RDI-02: one-container robot startup

**definition:** Starts the API and ROS bridge as one robot deployment unit.

**specification:**

- Start one API worker and one bridge process, and stop the container if either process exits.
- The bridge discovers the current non-terminal robot run, skips images while no run exists, and reconnects after release and restart.
- Keep the camera, result, and annotated-image topics configurable, with `/camera/image_raw`, `/surgint/robot_results`, and `/surgint_image` as defaults.

**verification:** Runtime tests cover active-run discovery, no-run behavior, terminal-run behavior, process startup, and clean shutdown.

### B.3 RDI-03: robot-host operation

**definition:** Connects the container to the robot's ROS graph and NVIDIA GPU with one documented command.

**specification:**

- Support x86-64 Linux with the NVIDIA Container Toolkit and ROS 2 Humble peers.
- Use host networking and IPC for ROS 2 discovery and local operator access.
- Publish unchanged frame response JSON as `std_msgs/msg/String` on the configured result topic.
- While the annotated-image topic has a subscriber, publish each analyzed camera image as `sensor_msgs/msg/Image` (`rgb8`, original header) with every tracked box, label, confidence, and the item's handling outcome drawn on it. The outcome persists on the item's box after its resolution frame.

**verification:** A local GPU smoke test starts the image, creates a run, replays ROS images, observes results and an annotated image, and confirms the operator page is reachable.

## C. shared constraints

- Preserve `OR-002` through `OR-004`, `OR-101` through `OR-105`, `AC-001`, `AC-003`, `AC-006`, and `AC-008` through `AC-010`.
- Reuse the shared detector, tracking, inventory, decision support, frame contract, and selection rule.
- Keep ROS imports and dependencies in the bridge and robot image, outside `services`, `surgint`, and `pyproject.toml`.
- Leave the existing tray-service image and tray-session behavior unchanged.

## D. package acceptance

- The dedicated image builds reproducibly with the pinned release model and starts without downloading artifacts at runtime.
- One container starts a ready CUDA API and ROS 2 bridge, attaches to an operator-created run, and republishes results into ROS.
- The existing production image still builds and its tray smoke test passes.
- The robot image has an independent versioned publication path and concise pull-and-run instructions.

## E. non-goals

- NVIDIA Jetson or ARM64 packaging;
- robot motion, actuation, planning, or execution control;
- robot-specific performance claims or hardware tuning;
- changing the shared result meaning, model, ontology, policy, or tray lifecycle;
- fixing the final ROS topic contract before the robot integration colleague confirms it.
