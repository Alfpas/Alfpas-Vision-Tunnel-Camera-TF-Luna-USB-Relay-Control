
import hid
import time

VID = 0x16C0
PID = 0x05DF

def control_relay(channel, state):
    if channel not in (1, 2):
        raise ValueError("Channel harus 1 atau 2")

    command = 0xFF if state else 0xFD
    packet = [0x00, command, channel, 0, 0, 0, 0, 0, 0]

    dev = hid.device()

    try:
        dev.open(VID, PID)
        result = dev.write(packet)

        if result <= 0:
            raise OSError("Gagal mengirim perintah")

        print(
            f"Relay {channel}: "
            f"{'ON' if state else 'OFF'} "
            "(perintah terkirim)"
        )

    finally:
        dev.close()


def main():
    while True:
        print("\n=== VISION TUNNEL LIGHT CONTROL ===")
        print("1. Relay 1 ON")
        print("2. Relay 1 OFF")
        print("3. Relay 2 ON")
        print("4. Relay 2 OFF")
        print("5. Test Relay 1 (ON 2 detik, OFF)")
        print("6. Test Relay 2 (ON 2 detik, OFF)")
        print("Q. Keluar")

        choice = input("Pilih: ").strip().lower()

        try:
            if choice == "1":
                control_relay(1, True)
            elif choice == "2":
                control_relay(1, False)
            elif choice == "3":
                control_relay(2, True)
            elif choice == "4":
                control_relay(2, False)
            elif choice in ("5", "6"):
                channel = 1 if choice == "5" else 2
                try:
                    control_relay(channel, True)
                    time.sleep(2)
                finally:
                    control_relay(channel, False)
            elif choice == "q":
                break
            else:
                print("Pilihan tidak valid")
        except (OSError, ValueError) as e:
            print("[ERROR]", e)


if __name__ == "__main__":
    main()
