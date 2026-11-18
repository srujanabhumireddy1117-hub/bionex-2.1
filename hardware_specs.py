from typing import Dict, Any

ESP32_PINOUT_MAP = {
    "microcontroller": "ESP32 DevKit V1 (30-pin)",
    "motor_driver": "TB6612FNG Dual H-Bridge Motor Driver",
    "connections": [
        {"gpio": "GPIO 25", "function": "PWMA", "description": "Left Motor PWM Speed Control"},
        {"gpio": "GPIO 26", "function": "AIN1", "description": "Left Motor Direction In 1"},
        {"gpio": "GPIO 27", "function": "AIN2", "description": "Left Motor Direction In 2"},
        {"gpio": "GPIO 14", "function": "PWMB", "description": "Right Motor PWM Speed Control"},
        {"gpio": "GPIO 32", "function": "BIN1", "description": "Right Motor Direction In 1"},
        {"gpio": "GPIO 33", "function": "BIN2", "description": "Right Motor Direction In 2"},
        {"gpio": "GPIO 13", "function": "STBY", "description": "Motor Standby / Hardware Enable"},
        {"gpio": "GPIO 18", "function": "INPUT", "description": "Tray Presence Digital Sensor"},
        {"gpio": "GPIO 19", "function": "INPUT", "description": "Emergency Stop Status Sense (Relay auxiliary)"},
        {"gpio": "GPIO 34", "function": "HX711 DOUT", "description": "Tray Load Cell Weight ADC Data"},
        {"gpio": "GPIO 23", "function": "HX711 SCK", "description": "Tray Load Cell Weight ADC Clock"},
        {"gpio": "GPIO 21", "function": "I2C SDA", "description": "PCA9685 16-Channel PWM Servo Controller Data"},
        {"gpio": "GPIO 22", "function": "I2C SCL", "description": "PCA9685 16-Channel PWM Servo Controller Clock"},
        {"gpio": "GPIO 17", "function": "UART2 TX", "description": "Serial Transmit to RPi / Jetson Host"},
        {"gpio": "GPIO 16", "function": "UART2 RX", "description": "Serial Receive from RPi / Jetson Host"},
        {"gpio": "GPIO 35", "function": "ADC1 CH7", "description": "Battery Voltage Sense (via Resistor Divider)"},
        {"gpio": "GPIO 36", "function": "ENCODER_L", "description": "Left Wheel Quadrature Optical Encoder A"},
        {"gpio": "GPIO 39", "function": "ENCODER_R", "description": "Right Wheel Quadrature Optical Encoder A"},
    ],
    "pca9685_channels": [
        {"channel": "CH 0", "assignment": "Robotic Arm - Base Rotation (0-180°)"},
        {"channel": "CH 1", "assignment": "Robotic Arm - Shoulder Elevation"},
        {"channel": "CH 2", "assignment": "Robotic Arm - Elbow Extension"},
        {"channel": "CH 3", "assignment": "Robotic Arm - Wrist Pitch"},
        {"channel": "CH 4", "assignment": "Robotic Arm - 2-Finger End Gripper"},
        {"channel": "CH 5", "assignment": "Yellow Compartment Sealed Gate Actuator"},
        {"channel": "CH 6", "assignment": "Red Compartment Sealed Gate Actuator"},
        {"channel": "CH 7", "assignment": "White (Sharps) Compartment Sealed Gate Actuator"},
        {"channel": "CH 8", "assignment": "Blue Compartment Sealed Gate Actuator"},
    ]
}

ROS2_TOPICS_SPEC = [
    {
        "topic": "/bionex/cmd_vel",
        "msg_type": "geometry_msgs/msg/Twist",
        "description": "Linear and angular velocity commands computed by Nav2 planner",
        "frequency": "20 Hz"
    },
    {
        "topic": "/bionex/odom",
        "msg_type": "nav_msgs/msg/Odometry",
        "description": "Robot wheel odometry and fused IMU pose estimation",
        "frequency": "50 Hz"
    },
    {
        "topic": "/bionex/scan",
        "msg_type": "sensor_msgs/msg/LaserScan",
        "description": "2D LiDAR / ToF range scan for real-time obstacle avoidance in hospital corridors",
        "frequency": "10 Hz"
    },
    {
        "topic": "/bionex/tray_presence",
        "msg_type": "std_msgs/msg/Bool",
        "description": "True when waste item is placed onto enclosed intake scale",
        "frequency": "Event-driven / 5 Hz"
    },
    {
        "topic": "/bionex/bin_fill",
        "msg_type": "bionex_msgs/msg/BinStatus",
        "description": "Ultrasonic depth measurements for Yellow, Red, White, and Blue compartments",
        "frequency": "1 Hz"
    },
    {
        "topic": "/bionex/estop_status",
        "msg_type": "std_msgs/msg/Bool",
        "description": "True when physical hardware emergency stop switch is depressed",
        "frequency": "50 Hz"
    }
]

MQTT_PAYLOAD_EXAMPLES = {
    "telemetry_topic": "bionex/amr/01/telemetry",
    "telemetry_sample": {
        "robot_id": "BIONEX-AMR-01",
        "timestamp": 1731846000,
        "battery": {"percent": 92, "voltage_v": 24.8, "current_a": 1.4},
        "location": {"zone": "Ward A", "x": 14.2, "y": 8.6, "heading_deg": 180},
        "status": "NAVIGATING",
        "current_waypoint": "Rm 102",
        "bins": {
            "yellow": {"fill_percent": 35, "weight_g": 1400},
            "red": {"fill_percent": 50, "weight_g": 2100},
            "white": {"fill_percent": 20, "weight_g": 650},
            "blue": {"fill_percent": 15, "weight_g": 800}
        },
        "sensors": {
            "obstacle_distance_m": 2.8,
            "tray_occupied": False,
            "e_stop": False,
            "mcu_uptime_s": 8420
        }
    },
    "alert_topic": "bionex/amr/01/alerts",
    "alert_sample": {
        "robot_id": "BIONEX-AMR-01",
        "severity": "WARNING",
        "event": "BIN_THRESHOLD_EXCEEDED",
        "message": "Red compartment reached 80% capacity limit. Sanitation requested.",
        "timestamp": 1731846050
    }
}


def get_hardware_specs() -> Dict[str, Any]:
    return {
        "esp32_pinout": ESP32_PINOUT_MAP,
        "ros2_topics": ROS2_TOPICS_SPEC,
        "mqtt_payloads": MQTT_PAYLOAD_EXAMPLES
    }
