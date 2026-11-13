
import cv2
import subprocess
import re
import os
import time
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================

CAMERA = "/dev/video0"

PREVIEW_WIDTH = 1280
PREVIEW_HEIGHT = 720

SAVE_DIR = "arducam_max_capture"
os.makedirs(SAVE_DIR, exist_ok=True)

# ==========================================
# DETECT CAMERA RESOLUTIONS
# ==========================================

def get_camera_modes(device):
    result = subprocess.run(
        [
            "v4l2-ctl",
            "-d", device,
            "--list-formats-ext"
        ],
        capture_output=True,
        text=True,
        check=True
    )

    modes = []
    current_format = None

    for line in result.stdout.splitlines():

        fmt = re.search(
            r"\[\d+\]: '(\w{4})'",
            line
        )

        if fmt:
            current_format = fmt.group(1)

        size = re.search(
            r"Size: Discrete (\d+)x(\d+)",
            line
        )

        if size and current_format:
            width = int(size.group(1))
            height = int(size.group(2))

            modes.append((
                width,
                height,
                current_format
            ))

    return modes


print("======================================")
print("ARDUCAM MAXIMUM RESOLUTION TEST")
print("======================================")

modes = get_camera_modes(CAMERA)

if not modes:
    raise RuntimeError(
        "Tidak ada mode resolusi discrete yang ditemukan"
    )

print("\nAvailable camera modes:")

for w, h, fmt in modes:
    print(f"{w} x {h} | {fmt}")

# Pilih resolusi terbesar berdasarkan total piksel
modes.sort(
    key=lambda x: x[0] * x[1],
    reverse=True
)

width, height, pixel_format = modes[0]

print("\nSelected maximum resolution:")
print(f"{width} x {height}")
print(f"Pixel format: {pixel_format}")

# ==========================================
# OPEN CAMERA
# ==========================================

cap = cv2.VideoCapture(
    CAMERA,
    cv2.CAP_V4L2
)

if not cap.isOpened():
    raise RuntimeError("Camera failed to open")

cap.set(
    cv2.CAP_PROP_FOURCC,
    cv2.VideoWriter_fourcc(*pixel_format)
)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

# Reduce buffer latency
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

actual_width = int(
    cap.get(cv2.CAP_PROP_FRAME_WIDTH)
)

actual_height = int(
    cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
)

actual_fps = cap.get(cv2.CAP_PROP_FPS)

print("\nActual camera settings:")
print(f"Resolution: {actual_width} x {actual_height}")
print(f"FPS setting: {actual_fps}")

# ==========================================
# MAIN LOOP
# ==========================================

previous_time = time.perf_counter()
fps = 0

print("\nControls:")
print("SPACE = Capture full resolution")
print("Q     = Quit")

try:
    while True:

        ret, frame = cap.read()

        if not ret:
            print("Frame capture failed")
            break

        now = time.perf_counter()
        dt = now - previous_time
        previous_time = now

        if dt > 0:
            instant_fps = 1.0 / dt
            fps = 0.9 * fps + 0.1 * instant_fps

        # Resize only the preview.
        # Original image resolution remains unchanged.
        h, w = frame.shape[:2]

        scale = min(
            PREVIEW_WIDTH / w,
            PREVIEW_HEIGHT / h,
            1.0
        )

        preview = cv2.resize(
            frame,
            (
                int(w * scale),
                int(h * scale)
            )
        )

        cv2.putText(
            preview,
            "ARDUCAM MAX RESOLUTION",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        cv2.putText(
            preview,
            f"Resolution: {w}x{h}",
            (20, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2
        )

        cv2.putText(
            preview,
            f"FPS: {fps:.1f}",
            (20, 110),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 255),
            2
        )

        cv2.imshow(
            "VISION TUNNEL - ARDUCAM MAX",
            preview
        )

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

        elif key == 32:

            filename = datetime.now().strftime(
                "arducam_%Y%m%d_%H%M%S_%f.jpg"
            )

            path = os.path.join(
                SAVE_DIR,
                filename
            )

            if cv2.imwrite(path, frame):
                print(f"[CAPTURE] Saved: {path}")
                print(f"[CAPTURE] Resolution: {w}x{h}")
            else:
                print("[ERROR] Failed to save image")

finally:
    cap.release()
    cv2.destroyAllWindows()

    print("\nCamera test finished")
