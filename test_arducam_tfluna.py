
import cv2
import serial
import serial.tools.list_ports
import time
import threading

# ==========================================
# KONFIGURASI
# ==========================================

CAMERA_INDEX = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
CAMERA_FPS = 30

TF_PORT = "/dev/ttyUSB0"
TF_BAUD = 115200

# ==========================================
# DATA SENSOR
# ==========================================

distance = None
strength = None
temperature = None
sensor_connected = False
running = True

# ==========================================
# THREAD SENSOR TF-LUNA
# ==========================================

def read_tfluna():
    global distance, strength, temperature
    global sensor_connected, running

    while running:
        try:
            print(f"[TF-Luna] Connecting {TF_PORT}")

            with serial.Serial(
                TF_PORT,
                TF_BAUD,
                timeout=0.2
            ) as ser:

                sensor_connected = True
                print("[TF-Luna] Connected")

                while running:
                    first = ser.read(1)

                    if first != b'\x59':
                        continue

                    second = ser.read(1)

                    if second != b'\x59':
                        continue

                    payload = ser.read(7)

                    if len(payload) != 7:
                        continue

                    frame = b'\x59\x59' + payload

                    checksum = sum(frame[:8]) & 0xFF

                    if checksum != frame[8]:
                        continue

                    distance = frame[2] | (frame[3] << 8)
                    strength = frame[4] | (frame[5] << 8)

                    raw_temp = frame[6] | (frame[7] << 8)
                    temperature = raw_temp / 8.0 - 256

        except serial.SerialException as e:
            sensor_connected = False
            print("[TF-Luna] Error:", e)

            if running:
                time.sleep(2)

    sensor_connected = False


# ==========================================
# START SENSOR THREAD
# ==========================================

thread = threading.Thread(
    target=read_tfluna,
    daemon=True
)

thread.start()

# ==========================================
# START CAMERA
# ==========================================

print("[CAMERA] Opening Arducam...")

cap = cv2.VideoCapture(
    CAMERA_INDEX,
    cv2.CAP_V4L2
)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)

if not cap.isOpened():
    print("[ERROR] Camera not detected")
    running = False
    raise SystemExit(1)

print("[CAMERA] Connected")

# ==========================================
# FPS COUNTER
# ==========================================

prev_time = time.time()
fps = 0

# ==========================================
# MAIN LOOP
# ==========================================

try:
    while True:

        ret, frame = cap.read()

        if not ret:
            print("[ERROR] Camera frame failed")
            break

        current_time = time.time()
        dt = current_time - prev_time

        if dt > 0:
            fps = 1.0 / dt

        prev_time = current_time

        # ----------------------------------
        # CAMERA INFORMATION
        # ----------------------------------

        cv2.putText(
            frame,
            "ARDUCAM + TF-LUNA TEST",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
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

        # ----------------------------------
        # TF-LUNA INFORMATION
        # ----------------------------------

        if sensor_connected and distance is not None:

            cv2.putText(
                frame,
                f"Distance: {distance} cm",
                (20, 130),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 255),
                2
            )

            cv2.putText(
                frame,
                f"Strength: {strength}",
                (20, 170),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                f"Temperature: {temperature:.1f} C",
                (20, 210),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )

        else:

            cv2.putText(
                frame,
                "TF-Luna: Waiting for data...",
                (20, 130),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )

        # ----------------------------------
        # CENTER CROSSHAIR
        # ----------------------------------

        h, w = frame.shape[:2]

        center_x = w // 2
        center_y = h // 2

        cv2.drawMarker(
            frame,
            (center_x, center_y),
            (0, 255, 0),
            cv2.MARKER_CROSS,
            25,
            2
        )

        # ----------------------------------
        # DISPLAY
        # ----------------------------------

        cv2.imshow(
            "Vision Tunnel - Camera & TF-Luna",
            frame
        )

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    running = False
    cap.release()
    cv2.destroyAllWindows()

    print("[SYSTEM] Test finished")
