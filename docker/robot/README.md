# Robot image

The robot image runs the CUDA API and ROS 2 Humble bridge in one x86-64 container. It is separate from the tray-service image.

## Pull and run

```bash
docker pull ghcr.io/ahmedghita1/surgint-instruments-robot:<version>

docker run --rm --gpus all \
  --network host \
  --ipc host \
  --name surgint-robot \
  -e ROS_DOMAIN_ID=0 \
  -e SURGINT_IMAGE_TOPIC=/camera/image_raw \
  -e SURGINT_RESULT_TOPIC=/surgint/robot_results \
  ghcr.io/ahmedghita1/surgint-instruments-robot:<version>
```

Open `http://ROBOT_IP:7860/robot`, start a run, and leave the container running. The bridge automatically attaches to that run. Results are also published as `std_msgs/msg/String` on `/surgint/robot_results`.

While something subscribes to `/surgint/annotated_image`, each analyzed camera image is published there as `sensor_msgs/msg/Image` with every box, label, confidence, and handling outcome drawn on it. View it with `ros2 run rqt_image_view rqt_image_view /surgint/annotated_image` or in rviz2.

Set `SURGINT_API_PORT` if port 7860 is occupied. Set `ROS_DOMAIN_ID`, `SURGINT_IMAGE_TOPIC`, `SURGINT_RESULT_TOPIC`, and `SURGINT_ANNOTATED_TOPIC` to match the robot.

The image contains the pinned model and does not download artifacts at startup. It does not support Jetson or ARM64.
