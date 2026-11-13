
import serial
import serial.tools.list_ports
import time

# =====================================
# KONFIGURASI TF-LUNA
# =====================================

PORT = "/dev/ttyUSB0"
BAUDRATE = 115200

MIN_DISTANCE = 50
MAX_DISTANCE = 200

# =====================================
# CEK PORT USB
# =====================================

print("=" * 55)
print("VISION TUNNEL - TF-LUNA SENSOR TEST")
print("=" * 55)

print("\nPort serial tersedia:")

for port in serial.tools.list_ports.comports():
    print(f"  {port.device} - {port.description}")

print("\nMenghubungkan TF-Luna...")

# =====================================
# KONEKSI SENSOR
# =====================================

try:
    ser = serial.Serial(
        PORT,
        BAUDRATE,
        timeout=1
    )

    print(f"[OK] TF-Luna connected: {PORT}")
    print(f"[OK] Baudrate: {BAUDRATE}")

except serial.SerialException as e:
    print("[ERROR] Gagal menghubungkan sensor")
    print(e)
    raise SystemExit(1)

# =====================================
# MEMBACA DATA SENSOR
# =====================================

print("\nMulai membaca data...")
print("Tekan CTRL+C untuk berhenti\n")

total_frames = 0
valid_frames = 0
invalid_frames = 0

start_time = time.monotonic()

try:
    while True:

        # Cari header paket TF-Luna
        if ser.read(1) != b'\x59':
            continue

        if ser.read(1) != b'\x59':
            continue

        payload = ser.read(7)

        if len(payload) != 7:
            continue

        frame = b'\x59\x59' + payload

        total_frames += 1

        # Verifikasi checksum
        checksum = sum(frame[:8]) & 0xFF

        if checksum != frame[8]:
            invalid_frames += 1
            continue

        valid_frames += 1

        # Parsing data
        distance = frame[2] | (frame[3] << 8)
        strength = frame[4] | (frame[5] << 8)

        raw_temp = frame[6] | (frame[7] << 8)
        temperature = raw_temp / 8.0 - 256

        # =================================
        # STATUS DETEKSI
        # =================================

        if distance == 0:
            status = "NO OBJECT"

        elif MIN_DISTANCE <= distance <= MAX_DISTANCE:
            status = "OBJECT DETECTED"

        elif distance < MIN_DISTANCE:
            status = "TOO CLOSE"

        else:
            status = "TOO FAR"

        # =================================
        # STATISTIK
        # =================================

        elapsed = time.monotonic() - start_time

        sensor_rate = (
            valid_frames / elapsed
            if elapsed > 0 else 0
        )

        # =================================
        # OUTPUT
        # =================================

        print(
            f"Distance: {distance:4d} cm | "
            f"Strength: {strength:5d} | "
            f"Temp: {temperature:5.1f} C | "
            f"Status: {status:16s} | "
            f"Rate: {sensor_rate:5.1f} Hz"
        )

except KeyboardInterrupt:
    print("\n\nPengujian dihentikan")

finally:
    ser.close()

    print("\n" + "=" * 55)
    print("TF-LUNA TEST SUMMARY")
    print("=" * 55)

    print("Total frames  :", total_frames)
    print("Valid frames  :", valid_frames)
    print("Invalid frames:", invalid_frames)

    if total_frames > 0:
        success_rate = valid_frames / total_frames * 100
        print(f"Success rate  : {success_rate:.2f}%")

    print("Sensor disconnected")
