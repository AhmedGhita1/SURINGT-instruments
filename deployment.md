# Robot Deployment Guide

## Hardware

- **Architecture:** `x86_64`
- **GPU:** NVIDIA GeForce RTX 4060, 8 GB VRAM
- **NVIDIA driver:** `580.178.04`
- **Driver maximum CUDA version:** 13.0
- **SURGINT container CUDA runtime:** 12.1
- **Docker GPU access:** Verified with the NVIDIA CUDA 12.1 container
- **ROS domain:** `1`

## ROS 2 Humble Topics

### Camera information

- **Topic:** `/camera/camera/color/camera_info`
- **Type:** `sensor_msgs/msg/CameraInfo`
- SURGINT records this interface but does not subscribe to it.

### Camera image input

- **Topic:** `/camera/camera/color/image_raw`
- **Type:** `sensor_msgs/msg/Image`
- The SURGINT bridge subscribes to this topic.

### SURGINT result output

- **Topic:** `/surgint/robot_results`
- **Type:** `std_msgs/msg/String`
- Each message contains the unchanged SURGINT frame-response JSON.

### SURGINT annotated image output

- **Topic:** `/surgint_image`
- **Type:** `sensor_msgs/msg/Image`, `rgb8`, with the camera image header
- Each analyzed camera image with every detected box, its label, confidence, and handling outcome drawn on it.
- Box colors: green for a recommendation, amber for `Needs review`, blue for an item without an outcome.
- SURGINT draws and publishes these images only while the topic has a subscriber.

## Step-by-Step Robot Deployment

1. Open a terminal on the robot and load ROS 2 Humble.

   ```bash
   source /opt/ros/humble/setup.bash
   ```

2. Confirm the camera topic types.

   ```bash
   ros2 topic type /camera/camera/color/camera_info
   ros2 topic type /camera/camera/color/image_raw
   ```

   Expected output:

   ```text
   sensor_msgs/msg/CameraInfo
   sensor_msgs/msg/Image
   ```

3. Confirm the camera is publishing images.

   ```bash
   timeout 10 ros2 topic hz /camera/camera/color/image_raw
   ```

4. Check the ROS domain used by the robot.

   ```bash
   echo "${ROS_DOMAIN_ID:-0}"
   ```

   The value printed here must be passed to the container. This robot uses `1`.

5. Download the SURGINT robot image.

   ```bash
   docker pull ghcr.io/ahmedghita1/surgint-instruments-robot:0.2.0
   ```

6. Check that port `7860` is free.

   ```bash
   ss -ltn | grep ':7860'
   ```

   No output means the port is free. A running older SURGINT container also uses this port and is replaced in the next step.

7. Remove any older SURGINT container, then start the new one. Replace `1` below if step 4 printed a different ROS domain.

   ```bash
   docker rm -f surgint-robot

   docker run -d \
     --name surgint-robot \
     --restart unless-stopped \
     --gpus all \
     --network host \
     --ipc host \
     -e ROS_DOMAIN_ID=1 \
     -e SURGINT_IMAGE_TOPIC=/camera/camera/color/image_raw \
     -e SURGINT_RESULT_TOPIC=/surgint/robot_results \
     -e SURGINT_ANNOTATED_TOPIC=/surgint_image \
     -e OMP_NUM_THREADS=2 \
     -e MKL_NUM_THREADS=2 \
     ghcr.io/ahmedghita1/surgint-instruments-robot:0.2.0
   ```

   `docker rm -f` prints an error when no older container exists. That error is harmless.

   `OMP_NUM_THREADS` and `MKL_NUM_THREADS` limit PyTorch to two CPU threads. Without them, PyTorch uses every CPU core. Raise both to `4` if the run analyzes fewer than five frames per second.

8. Wait up to two minutes, then inspect startup.

   ```bash
   docker ps --filter name=surgint-robot
   curl -s http://127.0.0.1:7860/health/ready
   docker logs surgint-robot 2>&1 | grep bridging
   ```

   - `docker ps` shows `Up ... (healthy)`. `(health: starting)` means the model is still loading.
   - The health response is `{"status":"ready"}`.
   - The log line names the camera topic, `/surgint/robot_results`, and `/surgint_image`.

9. Confirm that the bridge subscribed to the camera.

   ```bash
   ros2 topic info -v /camera/camera/color/image_raw
   ```

   The subscribers include the node `surgint_robot_image_bridge`.

10. Start a robot run. The bridge deliberately skips camera images while no run is active.

    ```bash
    curl -s -X POST http://127.0.0.1:7860/v1/robot-runs \
      -H "Content-Type: application/json" \
      -d '{"workflow_stage":"post-procedure-clearing","contamination_state":"not-regulated","use_state":"used"}'
    ```

    The response contains `"state":"active"` and the `run_id`. The run context decides the handling outcomes. Every handling rule requires `post-procedure-clearing` and `not-regulated`. Any other context returns `Needs review` for every item.

    A run can also be started from `http://ROBOT_IP:7860/robot` (find `ROBOT_IP` with `hostname -I`). The page shows only runs that were started from the page.

11. Confirm that SURGINT analyzes camera images.

    ```bash
    curl -s http://127.0.0.1:7860/v1/robot-runs/active | grep -o '"frame_count":[0-9]*'
    ```

    Run it twice, ten seconds apart. `frame_count` rises by about 50, which is five analyzed images per second.

12. Confirm that SURGINT publishes results.

    ```bash
    timeout 30 ros2 topic echo --once --full-length /surgint/robot_results
    ```

    With instruments in view, `detections` lists each instrument with `label`, `score`, and `box`.

13. View the annotated image.

    ```bash
    ros2 run rqt_image_view rqt_image_view /surgint_image
    ```

    In rviz2, add an `Image` display with the topic `/surgint_image` instead. Without a display, confirm the rate:

    ```bash
    timeout 10 ros2 topic hz /surgint_image
    ```

    The rate is about 5 Hz.

14. List the handling outcome of each resolved item.

    ```bash
    curl -s http://127.0.0.1:7860/v1/robot-runs/active | python3 -c "import json,sys; [print(r['item_id'], r['label'], round(r['confidence'],2), r['handling_outcome'], r['action'], '|', r['reason']) for r in json.load(sys.stdin)['results']]"
    ```

15. Stop the run and print its summary. Replace `RUN_ID` with the `run_id` from step 10.

    ```bash
    curl -s -X POST http://127.0.0.1:7860/v1/robot-runs/RUN_ID/stop | python3 -m json.tool
    curl -s -X DELETE http://127.0.0.1:7860/v1/robot-runs/RUN_ID
    ```

    The second command releases the run so that a new one can start.

16. Use the normal container controls as needed.

    ```bash
    docker logs -f surgint-robot
    docker stop surgint-robot
    docker start surgint-robot
    ```

    Runs exist only in memory. A container restart ends the current run.

## Common Failures

- **`unauthorized` while pulling:** The GHCR package is private or Docker is not logged in with a GitHub token that has `read:packages`.
- **`manifest unknown`:** Image version `0.2.0` was not published successfully.
- **Pull stops progressing:** Press `Ctrl+C` and run the same `docker pull` again. Completed layers are kept.
- **`could not select device driver`:** NVIDIA Container Toolkit is not working.
- **Port `7860` is occupied:** Stop the conflicting service or run SURGINT with `-e SURGINT_API_PORT=7861` and use port `7861` in the URLs.
- **No camera subscription:** Check the image topic, `sensor_msgs/msg/Image` type, ROS domain, firewall, VPN, and DDS network access.
- **`release the current robot run before starting another`:** A run is already active. Stop and release it as in step 15, or restart the container.
- **No result messages or annotated images:** Start a run first, then confirm that `frame_count` rises.
- **Every item is `Needs review`:** The run context matches no handling rule. Start a run with the context from step 10.
- **High CPU load:** Confirm that the container was started with `OMP_NUM_THREADS` and `MKL_NUM_THREADS`, then check `docker stats --no-stream surgint-robot`.
- **CUDA out of memory:** The RTX 4060 has 8 GB and another GPU service was already using about 2.25 GB. Stop that service during the first test if permitted.
- **`Could not load the custom kernel for multi-scale deformable attention`:** This warning was also seen in the verified image. The fallback is working if readiness returns HTTP 200 and ROS results appear.

## Draft Result Context

This result interface is a draft until the robot integration colleague confirms the final result topic, message type, and consumer requirements.

SURGINT publishes one JSON response for each camera frame that it selects and successfully processes. The response contains:

- Frame identity, camera sequence, source timestamp, and processing timing
- Detected instruments with label, confidence, bounding box, and tracking ID
- Newly resolved instrument items with stable item ID and class
- A handling outcome of `Recommendation` or `Needs review`, including the proposed action and reason
- New inventory entries and current per-class count
- Current run state, frame count, result count, and timing condition

The detection, result, and inventory lists can be empty when no instrument is detected or no new item is resolved in that frame.

Boxes are absolute pixel coordinates `[x1, y1, x2, y2]` in the camera image. An item's handling outcome appears in `new_results` only in the response for the frame that resolves it. Its `item_id` equals the `track_id` of its detections, so later detections can be matched to that outcome.

The current ROS publications are:

- **Topic:** `/surgint/robot_results`
  - **Type:** `std_msgs/msg/String`
  - **Payload:** The complete frame-response JSON encoded as the string value
- **Topic:** `/surgint_image`
  - **Type:** `sensor_msgs/msg/Image`
  - **Payload:** The analyzed camera image with boxes, labels, confidences, and handling outcomes drawn on it

This output is perception, inventory, and decision-support information. It is not a robot movement, actuation, or safety command. A separate robot component may subscribe to the result topic and decide how to consume the information.

Simplified example payload:

```json
{
  "detections": [
    {
      "track_id": 3,
      "label": "syringe",
      "score": 0.91,
      "box": [120, 80, 310, 260]
    }
  ],
  "new_results": [
    {
      "item_id": 3,
      "label": "syringe",
      "handling_outcome": "Recommendation",
      "action": "...",
      "reason": "..."
    }
  ],
  "new_inventory_entries": [
    {
      "label": "syringe",
      "class_count": 1
    }
  ],
  "status": {
    "state": "active",
    "frame_count": 12
  }
}
```
