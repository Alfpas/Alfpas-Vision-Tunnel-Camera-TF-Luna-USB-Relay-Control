
import cv2
import os
import csv
import time
import threading
import queue
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================

CAMERA_1 = "/dev/video0"
CAMERA_2 = "/dev/video2"

WIDTH = 1280
HEIGHT = 900
TARGET_FPS = 30

PREVIEW_WIDTH = 640
PREVIEW_HEIGHT = 360

SAVE_DIR = "dual_camera_captures"
os.makedirs(SAVE_DIR, exist_ok=True)

# ==========================================
# OPEN CAMERA
# ==========================================

def open_camera(device):
    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)

    if not cap.isOpened():
        raise RuntimeError(f"Camera unavailable: {device}")

    cap.set(
        cv2.CAP_PROP_FOURCC,
        cv2.VideoWriter_fourcc(*"MJPG")
    )
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, TARGET_FPS)

    print(
        f"[CAMERA] {device}: "
        f"{cap.get(cv2.CAP_PROP_FRAME_WIDTH):.0f}x"
        f"{cap.get(cv2.CAP_PROP_FRAME_HEIGHT):.0f}"
    )

    return cap


cam1 = open_camera(CAMERA_1)

try:
    cam2 = open_camera(CAMERA_2)
except Exception:
    cam1.release()
    raise

# ==========================================
# BURST STATE
# ==========================================

burst_remaining = 0
burst_total = 0
burst_index = 0
burst_session = ""
burst_start = 0

capture_queue = queue.Queue(maxsize=200)
writer_stop = threading.Event()

stats_lock = threading.Lock()

stats = {
    "saved_pairs": 0,
    "failed_pairs": 0,
    "dropped_pairs": 0
}

# ==========================================
# BACKGROUND PHOTO WRITER
# ==========================================

def photo_writer():
    while not writer_stop.is_set() or not capture_queue.empty():
        try:
            item = capture_queue.get(timeout=0.1)
        except queue.Empty:
            continue

        session, index, f1, f2, timestamp = item

        path1 = os.path.join(
            SAVE_DIR,
            f"{session}_cam1_{index:04d}.jpg"
        )

        path2 = os.path.join(
            SAVE_DIR,
            f"{session}_cam2_{index:04d}.jpg"
        )

        start = time.perf_counter()

        ok1 = cv2.imwrite(path1, f1)
        ok2 = cv2.imwrite(path2, f2)

        save_ms = (time.perf_counter() - start) * 1000

        with stats_lock:
            if ok1 and ok2:
                stats["saved_pairs"] += 1
            else:
                stats["failed_pairs"] += 1

        log_path = os.path.join(
            SAVE_DIR,
            f"{session}_log.csv"
        )

        with open(log_path, "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([
                index,
                timestamp,
                int(ok1),
                int(ok2),
                round(save_ms, 2)
            ])

        capture_queue.task_done()


writer_thread = threading.Thread(
    target=photo_writer,
    daemon=True
)
writer_thread.start()

# ==========================================
# BURST FUNCTIONS
# ==========================================

def start_burst(count):
    global burst_remaining, burst_total
    global burst_index, burst_session, burst_start

    if burst_remaining > 0 or not capture_queue.empty():
        print("[BURST] Previous capture still processing")
        return

    burst_total = count
    burst_remaining = count
    burst_index = 0

    burst_session = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    burst_start = time.perf_counter()

    log_path = os.path.join(
        SAVE_DIR,
        f"{burst_session}_log.csv"
    )

    with open(log_path, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            "index",
            "timestamp",
            "camera1_saved",
            "camera2_saved",
            "save_time_ms"
        ])

    with stats_lock:
        stats["saved_pairs"] = 0
        stats["failed_pairs"] = 0
        stats["dropped_pairs"] = 0

    print(f"[BURST] Starting {count} photo pairs")


def enqueue_capture(frame1, frame2):
    global burst_index, burst_remaining

    burst_index += 1

    timestamp = datetime.now().isoformat(
        timespec="milliseconds"
    )

    try:
        capture_queue.put_nowait((
            burst_session,
            burst_index,
            frame1.copy(),
            frame2.copy(),
            timestamp
        ))

    except queue.Full:
        with stats_lock:
            stats["dropped_pairs"] += 1

    burst_remaining -= 1


# ==========================================
# MAIN LOOP
# ==========================================

previous_time = time.perf_counter()
fps = 0

print("===================================")
print("VISION TUNNEL - DUAL CAMERA TEST")
print("SPACE : Single Capture")
print("B     : Burst 30 pairs")
print("T     : Stress Test 100 pairs")
print("Q     : Quit")
print("===================================")

try:
    while True:

        ret1, frame1 = cam1.read()
        ret2, frame2 = cam2.read()

        if not ret1 or not ret2:
            print("[ERROR] Camera frame failure")
            break

        now = time.perf_counter()

        dt = now - previous_time
        previous_time = now

        if dt > 0:
            instant_fps = 1.0 / dt
            fps = 0.9 * fps + 0.1 * instant_fps

        # Burst capture original frames
        if burst_remaining > 0:
            enqueue_capture(frame1, frame2)

            if burst_remaining == 0:
                duration = time.perf_counter() - burst_start
                print(
                    f"[BURST] Enqueue complete: "
                    f"{burst_total} pairs in {duration:.2f}s"
                )

        # ==================================
        # PREVIEW
        # ==================================

        p1 = cv2.resize(
            frame1, (PREVIEW_WIDTH, PREVIEW_HEIGHT)
        )

        p2 = cv2.resize(
            frame2, (PREVIEW_WIDTH, PREVIEW_HEIGHT)
        )

        cv2.putText(
            p1, "CAMERA 1", (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9, (0, 255, 0), 2
        )

        cv2.putText(
            p2, "CAMERA 2", (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9, (0, 255, 0), 2
        )

        for preview in (p1, p2):
            cv2.putText(
                preview,
                f"Loop FPS: {fps:.1f}",
                (20, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )

            cv2.putText(
                preview,
                f"Burst: {burst_index}/{burst_total}",
                (20, 110),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2
            )

        combined = cv2.hconcat([p1, p2])

        cv2.imshow(
            "VISION TUNNEL - DUAL CAMERA BURST",
            combined
        )

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

        elif key == ord("b"):
            start_burst(30)

        elif key == ord("t"):
            start_burst(100)

        elif key == 32:
            start_burst(1)

finally:
    print("[SYSTEM] Waiting for photo writer...")
    cam1.release()
    cam2.release()

    capture_queue.join()
    writer_stop.set()
    writer_thread.join()

    cv2.destroyAllWindows()

    with stats_lock:
        print("===================================")
        print("FINAL CAPTURE STATISTICS")
        print("Saved pairs :", stats["saved_pairs"])
        print("Failed pairs:", stats["failed_pairs"])
        print("Dropped     :", stats["dropped_pairs"])
        print("===================================")
