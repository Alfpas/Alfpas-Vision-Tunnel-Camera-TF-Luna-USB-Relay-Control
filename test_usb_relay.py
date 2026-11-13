
import hid

VID = 0x16C0
PID = 0x05DF

print("=" * 45)
print("VISION TUNNEL - USB RELAY HID TEST")
print("=" * 45)

devices = hid.enumerate(VID, PID)

if not devices:
    print("[FAIL] USB relay tidak ditemukan")
    raise SystemExit(1)

dev = hid.device()

try:
    dev.open_path(devices[0]["path"])
    print("[PASS] USB HID berhasil dibuka")

    manufacturer = dev.get_manufacturer_string()
    product = dev.get_product_string()

    print("Manufacturer:", manufacturer)
    print("Product:", product)

    # Baca feature report tanpa mengubah relay.
    # Tidak semua perangkat mendukung report ini.
    try:
        report = dev.get_feature_report(0, 9)
        print("Feature report:", bytes(report).hex(" "))
    except OSError as e:
        print("Feature report tidak tersedia:", e)

except OSError as e:
    print("[FAIL] Tidak dapat membuka perangkat:", e)

finally:
    dev.close()

print("\nPengujian selesai.")
