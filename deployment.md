# Robot Deployment Guide

## Hardware

- **Architecture:** `x86_64`
- **GPU:** NVIDIA GeForce RTX 4060, 8 GB VRAM
- **NVIDIA driver:** `580.178.04`
- **Driver maximum CUDA version:** 13.0
- **SURGINT container CUDA runtime:** 12.1
- **Docker GPU access:** Verified with the NVIDIA CUDA 12.1 container

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

   The value printed here must be passed to the container. The default is `0`.

5. Download the SURGINT robot image.

   ```bash
   docker pull ghcr.io/ahmedghita1/surgint-instruments-robot:0.1.0
   ```

6. Check that port `7860` is free.

   ```bash
   ss -ltn | grep ':7860'
   ```

   No output means the port is free.

7. Start the robot container. Replace `0` below if step 4 printed a different ROS domain.

   ```bash
   docker run -d \
     --name surgint-robot \
     --restart unless-stopped \
     --gpus all \
     --network host \
     --ipc host \
     -e ROS_DOMAIN_ID=0 \
     -e SURGINT_IMAGE_TOPIC=/camera/camera/color/image_raw \
     -e SURGINT_RESULT_TOPIC=/surgint/robot_results \
     -e OMP_NUM_THREADS=2 \
     -e MKL_NUM_THREADS=2 \
     ghcr.io/ahmedghita1/surgint-instruments-robot:0.1.0
   ```

   `OMP_NUM_THREADS` and `MKL_NUM_THREADS` limit PyTorch to two CPU threads. Without them, PyTorch uses every CPU core. Raise both to `4` if the run analyzes fewer than five frames per second.

8. Wait up to two minutes, then inspect startup.

   ```bash
   docker ps --filter name=surgint-robot
   docker logs --tail 100 surgint-robot
   curl -i http://127.0.0.1:7860/health/ready
   ```

   The health response must be HTTP 200 with:

   ```json
   {"status":"ready"}
   ```

9. Find the robot IP address.

   ```bash
   hostname -I
   ```

10. From a browser on the same network, open:

    ```text
    http://ROBOT_IP:7860/robot
    ```

11. Start a robot run from the page. The bridge deliberately skips camera images while no run is active.

12. Confirm that the bridge subscribed to the camera.

    ```bash
    source /opt/ros/humble/setup.bash
    ros2 topic info -v /camera/camera/color/image_raw
    ```

13. Confirm that SURGINT publishes results.

    ```bash
    ros2 topic type /surgint/robot_results
    timeout 30 ros2 topic echo --once /surgint/robot_results
    ```

14. Use the normal container controls as needed.

    ```bash
    docker logs -f surgint-robot
    docker stop surgint-robot
    docker start surgint-robot
    ```

## Common Failures

- **`unauthorized` while pulling:** The GHCR package is private or Docker is not logged in with a GitHub token that has `read:packages`.
- **`manifest unknown`:** Image version `0.1.0` was not published successfully.
- **`could not select device driver`:** NVIDIA Container Toolkit is not working.
- **Container name already exists:** An older `surgint-robot` container is present. Inspect it before removing or replacing it.
- **Port `7860` is occupied:** Stop the conflicting service or run SURGINT with `-e SURGINT_API_PORT=7861` and use port `7861` in the URLs.
- **No camera subscription:** Check the image topic, `sensor_msgs/msg/Image` type, ROS domain, firewall, VPN, and DDS network access.
- **No result messages:** Start a run from `/robot` first, then confirm camera frames reach the bridge.
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

The current ROS publication is:

- **Topic:** `/surgint/robot_results`
- **Type:** `std_msgs/msg/String`
- **Payload:** The complete frame-response JSON encoded as the string value

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
      "item_id": 7,
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
