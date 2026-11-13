
import cv2
import serial
import threading
import time
import os
import subprocess
from datetime import datetime

# ======================================
# CONFIGURATION
# ======================================

CAMERA_INDEX = 0
CAMERA_DEVICE = "/dev/video0"

TF_PORT = "/dev/ttyUSB1"
TF_BAUD = 115200

WIDTH = 1280
HEIGHT = 900

MIN_DISTANCE = 50
MAX_DISTANCE = 200

BLUR_FOCUS = 0  # Nilai sementara, perlu kalibrasi
FOCUS_UPDATE_INTERVAL = 0.3

SAVE_DIR = "captures"
os.makedirs(SAVE_DIR, exist_ok=True)

# Example calibration only!
# Replace with measured distance/focus pairs.
FOCUS_TABLE = [
    (200, 500),
    (150, 750),
    (200, 900),
    (50, 1023)
]

MIN_STRENGTH = 100
FOCUS_UPDATE_INTERVAL = 0.3

# ======================================
# SHARED DATA
# ======================================

distance = None
strength = 0
sensor_ok = False
last_sensor_time = 0

running = True
auto_focus = True

current_focus = None
focus_supported = False

data_lock = threading.Lock()

# ======================================
# FOCUS CONTROL
# ======================================

def set_focus(value):
    global current_focus

    value = int(value)

    try:
        subprocess.run(
            [
                "v4l2-ctl",
                "-d", CAMERA_DEVICE,
                "-c", f"focus_absolute={value}"
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=2
        )

        current_focus = value
        return True

    except Exception as e:
        print("Focus error:", e)
        return False


def check_focus_support():
    try:
        result = subprocess.run(
            [
                "v4l2-ctl",
                "-d", CAMERA_DEVICE,
                "--list-ctrls"
            ],
            capture_output=True,
            text=True,
            timeout=3
        )

        return "focus_absolute" in result.stdout

    except Exception:
        return False


def distance_to_focus(cm):
    # Linear interpolation between calibration points
    table = FOCUS_TABLE

    if cm <= table[0][0]:
        return table[0][1]

    if cm >= table[-1][0]:
        return table[-1][1]

    for i in range(len(table) - 1):
        d1, f1 = table[i]
        d2, f2 = table[i + 1]

        if d1 <= cm <= d2:
            ratio = (cm - d1) / (d2 - d1)
            return round(f1 + ratio * (f2 - f1))

    return table[-1][1]


# ======================================
# TF-LUNA READER
# ======================================

def read_tfluna():
    global distance, strength
    global sensor_ok, last_sensor_time

    while running:
        try:
            with serial.Serial(
                TF_PORT, TF_BAUD, timeout=0.2
            ) as ser:

                print("TF-Luna connected:", TF_PORT)

                while running:
                    if ser.read(1) != b'\x59':
                        continue

                    if ser.read(1) != b'\x59':
                        continue

                    payload = ser.read(7)

                    if len(payload) != 7:
                        continue

                    frame = b'\x59\x59' + payload

                    if (sum(frame[:8]) & 0xFF) != frame[8]:
                        continue

                    d = frame[2] | (frame[3] << 8)
                    s = frame[4] | (frame[5] << 8)

                    with data_lock:
                        distance = d
                        strength = s
                        last_sensor_time = time.monotonic()
                        sensor_ok = True

        except serial.SerialException as e:
            print("TF-Luna error:", e)

            with data_lock:
                sensor_ok = False

            if running:
                time.sleep(2)


# ======================================
# MAIN PROGRAM
# ======================================

focus_supported = check_focus_support()

print("Focus control supported:", focus_supported)

cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2)

if not cap.isOpened():
    raise RuntimeError("Arducam not detected")

cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
cap.set(cv2.CAP_PROP_FPS, 30)

thread = threading.Thread(
    target=read_tfluna,
    daemon=True
)
thread.start()

last_focus_update = 0
previous_time = time.monotonic()

try:
    while True:
        ret, frame = cap.read()

        if not ret:
            print("Camera frame failed")
            break

        now = time.monotonic()

        fps = 1 / max(now - previous_time, 0.001)
        previous_time = now

        with data_lock:
            d = distance
            s = strength
            connected = sensor_ok
            age = now - last_sensor_time

        valid = (
            connected
            and age < 1.0
            and d is not None
            and d > 0
            and s >= MIN_STRENGTH
        )

        # ----------------------------------
        # FOCUS UPDATE
        # ----------------------------------

        if (
            auto_focus
            and focus_supported
            and valid
            and now - last_focus_update
                >= FOCUS_UPDATE_INTERVAL
        ):
            focus_value = distance_to_focus(d)

            if focus_value != current_focus:
                set_focus(focus_value)

            last_focus_update = now

        # ----------------------------------
        # OVERLAY
        # ----------------------------------

        cv2.putText(
            frame,
            "VISION TUNNEL - TF-LUNA FOCUS",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            f"FPS: {fps:.1f}",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        if valid:
            info = f"Distance: {d} cm"
            color = (0, 255, 255)
        else:
            info = "Distance: NO OBJECT"
            color = (0, 0, 255)

        cv2.putText(
            frame, info, (20, 125),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8, color, 2
        )

        cv2.putText(
            frame,
            f"Strength: {s}",
            (20, 165),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        focus_text = (
            f"Focus: {current_focus}"
            if focus_supported
            else "Focus: NOT SUPPORTED"
        )

        cv2.putText(
            frame,
            focus_text,
            (20, 205),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"TF Focus: {'ON' if auto_focus else 'OFF'}",
            (20, 245),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0) if auto_focus else (0, 0, 255),
            2
        )

        h, w = frame.shape[:2]

        cv2.drawMarker(
            frame,
            (w // 2, h // 2),
            (0, 255, 0),
            cv2.MARKER_CROSS,
            25,
            2
        )

        cv2.imshow("Vision Tunnel - TF Focus", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break

        elif key == ord('a'):
            auto_focus = not auto_focus
            print("TF focus:", auto_focus)

        elif key == 32:
            filename = datetime.now().strftime(
                "capture_%Y%m%d_%H%M%S_%f.jpg"
            )

            path = os.path.join(SAVE_DIR, filename)

            # Save original frame without overlay
            # For production, copy before drawing overlays.
            if cv2.imwrite(path, frame):
                print("Photo saved:", path)
            else:
                print("Failed to save photo")

finally:
    running = False
    cap.release()
    cv2.destroyAllWindows()


# ======================================
# FOCUS CONTROL TF-LUNA
# ======================================

if auto_focus and focus_supported:

    if now - last_focus_update >= FOCUS_UPDATE_INTERVAL:

        if valid and 50 <= d <= 200:
            # Objek berada dalam jangkauan
            target_focus = distance_to_focus(d)
            focus_status = "FOCUS ACTIVE"

        else:
            # Tidak ada objek atau di luar jangkauan
            target_focus = BLUR_FOCUS
            focus_status = "NO FOCUS"

        if target_focus != current_focus:
            set_focus(target_focus)

        last_focus_update = now

        