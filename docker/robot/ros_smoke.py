"""Publish ROS images and require one robot-result response."""

import json
from array import array
from time import monotonic

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String


TIMEOUT_SECONDS = 30.0


def main() -> None:
    rclpy.init()
    node = Node("surgint_robot_image_smoke")
    publisher = node.create_publisher(Image, "/camera/image_raw", qos_profile_sensor_data)
    responses: list[str] = []
    node.create_subscription(
        String,
        "/surgint/robot_results",
        lambda message: responses.append(message.data),
        10,
    )

    started_at = monotonic()
    while publisher.get_subscription_count() == 0 and monotonic() - started_at < 10.0:
        rclpy.spin_once(node, timeout_sec=0.1)
    if publisher.get_subscription_count() == 0:
        raise SystemExit("ROS image publisher did not discover the bridge subscriber")

    sequence = 0
    next_publish_at = started_at
    while not responses and monotonic() - started_at < TIMEOUT_SECONDS:
        now = monotonic()
        if now >= next_publish_at:
            message = Image()
            captured_at = 1.0 + sequence * 0.2
            message.header.stamp.sec = int(captured_at)
            message.header.stamp.nanosec = int((captured_at % 1.0) * 1e9)
            message.height = 8
            message.width = 12
            message.encoding = "rgb8"
            message.step = 36
            message.data = array("B", [114] * (message.height * message.step))
            publisher.publish(message)
            sequence += 1
            next_publish_at += 0.2
        rclpy.spin_once(node, timeout_sec=0.05)

    node.destroy_node()
    rclpy.shutdown()
    if not responses:
        raise SystemExit("no robot result received")
    payload = json.loads(responses[0])
    if payload["frame"]["source_id"] != "ros2-camera":
        raise SystemExit("result did not preserve the ROS source identity")
    print("ROS image reached the active run and its response returned on the result topic")


if __name__ == "__main__":
    main()
