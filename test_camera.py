
import cv2
import time
import os
from datetime import datetime

# =====================================
# CONFIGURATION
# =====================================

CAMERA = "/dev/video0"

WIDTH = 3840
HEIGHT = 2160
FPS_TARGET = 15

SAVE_DIR = "captures_4k"
os.makedirs(SAVE_DIR, exist_ok=True)

# =====================================
# OPEN CAMERA
# =====================================

cap = cv2.VideoCapture(CAMERA, cv2.CAP_V4L2)

if not cap.isOpened():
    raise RuntimeError("Arducam tidak terdeteksi")

# Gunakan format YUYV
cap.set(
    cv2.CAP_PROP_FOURCC,
    cv2.VideoWriter_fourcc(*"YUYV")
)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
cap.set(cv2.CAP_PROP_FPS, FPS_TARGET)

# Cek konfigurasi aktual
actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
actual_format = "".join(
    chr((fourcc >> (8 * i)) & 0xFF)
    for i in range(4)
)

print("=================================")
print("ARDUCAM 4K YUYV TEST")
print("=================================")
print("Resolution:", actual_width, "x", actual_height)
print("Format:", actual_format)
print("FPS setting:", cap.get(cv2.CAP_PROP_FPS))
print("SPACE = Capture 4K")
print("Q = Exit")
print("=================================")

if (
    actual_width != WIDTH
    or actual_height != HEIGHT
    or actual_format != "YUYV"
):
    print("[WARNING] Mode kamera berbeda dari permintaan!")

# =====================================
# MAIN LOOP
# =====================================

prev_time = time.perf_counter()
fps = 0

try:
    while True:

        ret, frame = cap.read()

        if not ret:
            print("[ERROR] Gagal membaca frame")
            break

        now = time.perf_counter()
        dt = now - prev_time
        prev_time = now

        if dt > 0:
            instant_fps = 1.0 / dt
            fps = 0.9 * fps + 0.1 * instant_fps

        # Simpan frame asli tanpa overlay
        original = frame

        # Preview diperkecil agar ringan
        preview = cv2.resize(
            frame,
            (1280, 720)
        )

        cv2.putText(
            preview,
            "ARDUCAM 4K YUYV",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )

        cv2.putText(
            preview,
            f"FPS: {fps:.1f}",
            (20, 85),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

        cv2.imshow("ARDUCAM 4K TEST", preview)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

        elif key == 32:

            filename = datetime.now().strftime(
                "arducam_4k_%Y%m%d_%H%M%S.jpg"
            )

            path = os.path.join(SAVE_DIR, filename)

            if cv2.imwrite(path, original):
                print("[CAPTURE] Saved:", path)
                print(
                    "[CAPTURE] Resolution:",
                    original.shape[1],
                    "x",
                    original.shape[0]
                )
            else:
                print("[ERROR] Gagal menyimpan foto")

finally:
    cap.release()
    cv2.destroyAllWindows()

print("Camera test selesai")
