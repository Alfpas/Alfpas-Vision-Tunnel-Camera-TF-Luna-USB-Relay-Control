
import serial
import time

PORT = "/dev/ttyUSB0"
BAUD = 115200

# Perintah query firmware TF-Luna
# Format protokol Benewake
GET_VERSION = bytes.fromhex("5A 04 01 5F")


def read_firmware_response(ser, timeout=2):
    deadline = time.monotonic() + timeout
    buffer = bytearray()

    while time.monotonic() < deadline:
        data = ser.read(ser.in_waiting or 1)
        buffer.extend(data)

        # Cari header respons perintah
        while len(buffer) >= 2:
            pos = buffer.find(b"\x5A")

            if pos < 0:
                buffer.clear()
                break

            if pos > 0:
                del buffer[:pos]

            if len(buffer) < 2:
                break

            length = buffer[1]

            if length < 4 or length > 64:
                del buffer[0]
                continue

            if len(buffer) < length:
                break

            frame = bytes(buffer[:length])
            del buffer[:length]

            if sum(frame[:-1]) & 0xFF != frame[-1]:
                continue

            if frame[2] == 0x01:
                return frame

    return None


try:
    with serial.Serial(PORT, BAUD, timeout=0.1) as ser:
        print("=" * 45)
        print("TF-LUNA UART TX/RX TEST")
        print("=" * 45)

        # =================================
        # TEST 1: SENSOR TX -> PC RX
        # =================================

        print("\n[TEST 1] Menerima data TF-Luna")

        buffer = bytearray()
        valid_frames = 0
        start = time.monotonic()

        while time.monotonic() - start < 3:
            buffer.extend(ser.read(ser.in_waiting or 1))

            while len(buffer) >= 9:
                pos = buffer.find(b"\x59\x59")

                if pos < 0:
                    del buffer[:-1]
                    break

                if pos > 0:
                    del buffer[:pos]

                if len(buffer) < 9:
                    break

                frame = bytes(buffer[:9])

                if sum(frame[:8]) & 0xFF == frame[8]:
                    valid_frames += 1
                    del buffer[:9]
                else:
                    del buffer[0]

        print("Frame valid:", valid_frames)

        if valid_frames:
            print("[PASS] TX TF-Luna -> RX USB")
        else:
            print("[FAIL] Tidak ada frame valid")

        # =================================
        # TEST 2: PC TX -> SENSOR RX
        # =================================

        print("\n[TEST 2] Mengirim perintah firmware")

        ser.reset_input_buffer()

        print("TX:", GET_VERSION.hex(" ").upper())

        ser.write(GET_VERSION)
        ser.flush()

        response = read_firmware_response(ser)

        if response:
            print("RX:", response.hex(" ").upper())
            print("[PASS] Komunikasi dua arah berhasil")

            if len(response) >= 7:
                print(
                    "Firmware version:",
                    ".".join(str(x) for x in response[3:6])
                )
        else:
            print("[WARNING] Tidak ada respons firmware")
            print("Periksa jalur PC TX -> TF-Luna RX")
            print("Periksa juga dukungan command firmware")

        print("\nPengujian selesai")

except serial.SerialException as e:
    print("[ERROR] Serial:", e)
