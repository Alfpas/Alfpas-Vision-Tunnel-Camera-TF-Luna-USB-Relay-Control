# Vision Tunnel — Camera, TF-Luna & USB Relay Control

Sistem **Vision Tunnel** berbasis **Linux Mint + Python** untuk pengujian kamera USB (Arducam), sensor jarak **Benewake TF-Luna**, dan pencahayaan AC melalui **USB HID Relay**. Repository ini ditujukan untuk **backup kode, dokumentasi pengujian, dan migrasi ke PC lain**.

> **Status:** tahap pengujian dan integrasi. Tidak semua fitur otomatis sudah selesai atau diverifikasi pada satu program terpadu.

## 📋 Fitur dan status

| Komponen / fitur | Status | Catatan |
|---|---|---|
| Kamera USB Arducam | Pernah diuji | Preview/capture melalui OpenCV; mode resolusi bergantung kamera |
| TF-Luna bawah | Pernah diuji | Pembacaan jarak serial 115200 baud |
| TF-Luna kiri | **UART TX/RX teruji** | 925 frame valid; respons firmware **1.5.3** |
| USB Relay HID | **Channel 1 teruji** | Berhasil menyalakan lampu Vision Tunnel |
| USB Relay channel 2 | Belum dipastikan | Belum diketahui apakah terhubung ke beban |
| Dua kamera sekaligus | Pengujian dalam pengembangan | Indeks kamera dan sinkronisasi perlu diverifikasi |
| Fokus kamera berbasis jarak | Rencana/pengembangan | Perlu dukungan kontrol fokus hardware dan kalibrasi |
| Capture otomatis dengan lampu | Rencana integrasi | Belum diklaim sebagai fitur selesai |

## 🏗️ Arsitektur sistem

```text
                   [ PC Linux Mint ]
                          |
                    [ Python App ]
                  /       |       \
                 /        |        \
       [ USB Camera ] [ USB-UART ] [ USB HID Relay ]
          Arducam      TF-Luna       16c0:05df
                        kiri /         |
                        bawah       Channel 1
                                       |
                              Lampu Vision Tunnel
```

Diagram adalah gambaran logis. Jalur listrik AC, pembagian lampu, dan koneksi fisik aktual perlu dikonfirmasi dari wiring mesin.

## 🔧 Hardware

| Perangkat | Keterangan |
|---|---|
| PC | Linux Mint, Python 3 dan virtual environment |
| Kamera | USB Arducam / kamera UVC; jumlah dan indeks tergantung konfigurasi |
| Sensor jarak | Benewake TF-Luna, antarmuka UART |
| Adapter serial | USB-to-UART untuk TF-Luna; **TX ↔ RX**, GND bersama |
| USB Relay | DCTTECH **USBRelay2**, VID `16c0`, PID `05df` |
| Pencahayaan | Lampu AC Vision Tunnel, dikontrol melalui relay |

**Keselamatan:** Lampu menggunakan tegangan AC 220 V. Putuskan sumber listrik sebelum memeriksa atau mengubah wiring. Gunakan enclosure, proteksi, dan relay dengan rating sesuai beban. Jangan menganggap perintah OFF dari Python sebagai pemutus darurat.

## 📂 Struktur proyek

Repository sebaiknya menyimpan **file program yang benar-benar ada**, bukan virtual environment atau data sementara. Contoh pengorganisasian yang dapat digunakan:

```text
VisionTunnel/
├── README.md
├── requirements.txt
├── .gitignore
├── test_tfluna.py          # Tes UART TF-Luna (jika tersedia)
├── test_usb_relay.py       # Deteksi / uji HID relay (jika tersedia)
├── control_lamp.py         # Kontrol lampu relay (jika tersedia)
├── test_camera.py          # Tes kamera (jika tersedia)
└── test_dual_camera.py     # Tes dua kamera (jika tersedia)
```

> Nama file di atas berasal dari skrip yang pernah dibahas dan **harus dicocokkan dengan isi folder `~/VisionTunnel`**. Jangan menganggap seluruhnya sudah ada atau sudah final.

## ⚙️ Instalasi di PC baru

### 1. Siapkan sistem

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip v4l-utils libhidapi-hidraw0
```

### 2. Clone repository

Ganti `<URL_REPOSITORY_VISION_TUNNEL>` dengan URL repository yang benar setelah dibuat di GitHub:

```bash
git clone <URL_REPOSITORY_VISION_TUNNEL> ~/VisionTunnel
cd ~/VisionTunnel
```

### 3. Buat virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
```

Jika `requirements.txt` sudah disertakan:

```bash
python -m pip install -r requirements.txt
```

Jika belum ada, instal paket yang digunakan pada pengujian sebelumnya:

```bash
python -m pip install opencv-python numpy pyserial hidapi
```

> Beberapa kamera khusus Arducam membutuhkan driver, SDK, atau paket tambahan yang tidak termasuk dalam daftar di atas. Cocokkan dengan skrip kamera yang benar-benar digunakan.

## 🔌 Identifikasi port dan perangkat

**Jangan menganggap nama port dari PC lama akan sama di PC baru.**

### Kamera

```bash
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --list-formats-ext
v4l2-ctl -d /dev/video0 --list-ctrls
```

Sesuaikan `/dev/video0` dengan perangkat aktual. Satu kamera dapat membuat lebih dari satu node `/dev/video*`.

### TF-Luna

```bash
ls -l /dev/serial/by-id/ 2>/dev/null
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
python -m serial.tools.list_ports -v
```

Parameter UART yang pernah digunakan:

```python
PORT = "/dev/ttyUSB1"  # CONTOH PC LAMA: ganti sesuai PC baru
BAUD = 115200
```

Jika ada beberapa adapter, gunakan `/dev/serial/by-id/...` atau aturan udev agar identifikasi sensor kiri dan bawah tidak tertukar.

**Wiring UART:** TX sensor → RX adapter; RX sensor ← TX adapter; GND → GND. Periksa suplai dan level logika berdasarkan spesifikasi modul.

### USB HID Relay

```bash
lsusb
```

Identitas yang pernah terbaca:

```text
16c0:05df — DCTTECH USBRelay2
Manufacturer: www.dcttech.com
Product: USBRelay2
Feature report: 00 48 55 52 54 4D 00 00 00
```

USB relay ini **bukan** perangkat `/dev/ttyUSB*`; akses dilakukan dengan `hidapi`.

## 🧪 Pengujian perangkat

Aktifkan lingkungan Python:

```bash
cd ~/VisionTunnel
source venv/bin/activate
```

Jalankan hanya file yang sudah tersedia di repository:

```bash
python test_camera.py
python test_tfluna.py
python test_usb_relay.py
```

**Hasil TF-Luna kiri yang pernah tercatat:**

```text
Frame valid: 925
[PASS] TX TF-Luna -> RX USB
TX: 5A 04 01 5F
RX: 5A 07 01 01 05 03 6B
[PASS] Komunikasi dua arah berhasil
Firmware version: 1.5.3
```

Hasil tersebut adalah catatan pengujian **sensor kiri**, bukan jaminan bahwa sensor bawah atau port pada PC baru identik.

### Kontrol lampu

USBRelay2 terdeteksi sebagai HID, dengan channel 1 berhasil menyalakan lampu. Jika file `control_lamp.py` sudah dimasukkan ke repository:

```bash
python control_lamp.py
```

Jika akses HID ditolak, lakukan pemeriksaan permission terlebih dahulu; saat pengujian sebelumnya perangkat dapat dibuka dengan interpreter virtual environment melalui `sudo`:

```bash
sudo ~/VisionTunnel/venv/bin/python ~/VisionTunnel/control_lamp.py
```

Gunakan `sudo` hanya untuk pengujian yang diperlukan. Untuk penggunaan rutin, konfigurasi izin `udev` yang terbatas lebih disarankan. **Jangan menguji lampu AC tanpa memastikan wiring aman.**

## 🛠️ Troubleshooting

| Masalah | Pemeriksaan |
|---|---|
| `ModuleNotFoundError: cv2` | Aktifkan `venv`, lalu instal `opencv-python` |
| TF-Luna tidak mengirim data | Cek port, TX/RX, GND, baudrate 115200, suplai dan izin serial |
| TF-Luna terbaca `0 cm` | Bisa berarti tidak ada pantulan/target valid; cek strength dan posisi objek |
| Kamera black screen | Cek node V4L2, format, resolusi, bandwidth USB, dan aplikasi lain yang memakai kamera |
| USB relay `open failed` | Cek permission `/dev/hidraw*` dan aturan udev |
| Relay 1 bekerja, relay 2 tidak | Cek apakah channel 2 dipakai, indikator klik, dan wiring beban; jangan langsung menyimpulkan rusak |
| Port berubah setelah pindah PC | Perbarui konfigurasi atau gunakan nama perangkat stabil di `/dev/serial/by-id/` |

## 📦 Backup dari PC lama

Di PC lama:

```bash
cd ~/VisionTunnel
find . -maxdepth 2 -type f | sort
source venv/bin/activate
python -m pip freeze > requirements.txt
```

Tinjau `requirements.txt` sebelum dipakai di PC baru: `pip freeze` dapat mencakup paket yang tidak diperlukan dan versi yang tidak cocok dengan platform baru.

Buat `.gitignore`:

```gitignore
venv/
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.env
.env.*
!.env.example
.vscode/
*.log
.DS_Store
```

**Periksa sebelum upload:** jangan commit password, token, kredensial, file sensitif, atau foto/data produksi yang tidak boleh dipublikasikan. Untuk repository perusahaan, pertimbangkan **Private repository**.

Setelah membuat repository kosong di GitHub:

```bash
cd ~/VisionTunnel
git init
git add .
git commit -m "Backup Vision Tunnel scripts and documentation"
git branch -M main
git remote add origin <URL_REPOSITORY_VISION_TUNNEL>
git push -u origin main
```

Jika repository sudah memiliki remote `origin`, periksa dengan `git remote -v` dan sesuaikan; jangan menambahkan remote yang sama dua kali. GitHub memerlukan autentikasi yang didukung, misalnya SSH key atau personal access token, bukan password akun biasa.

**Backup tambahan (opsional):** simpan salinan folder proyek dan konfigurasi hardware di media penyimpanan terpisah. GitHub tidak otomatis membackup file yang dikecualikan `.gitignore`.

## 🚀 Checklist migrasi

- [ ] Semua skrip penting sudah dicopy dan diperiksa
- [ ] `README.md`, `.gitignore`, dan `requirements.txt` sudah tersedia
- [ ] Repository GitHub berhasil di-push dan bisa di-clone
- [ ] PC baru berhasil menjalankan Python virtual environment
- [ ] Kamera terdeteksi dan preview/capture berhasil
- [ ] TF-Luna kiri terbaca pada port yang benar
- [ ] TF-Luna bawah terbaca pada port yang benar
- [ ] USBRelay2 terdeteksi melalui `lsusb`
- [ ] Relay channel 1 diuji aman tanpa beban AC sebelum pengujian lampu
- [ ] Seluruh lampu yang terhubung berfungsi sesuai wiring aktual
- [ ] Integrasi kamera, sensor, dan lampu diuji kembali

## 📝 Catatan pengembangan

Rencana berikutnya meliputi pengambilan gambar dua kamera, burst capture, pengaturan fokus berdasarkan jarak objek (sekitar 50–200 cm, bergantung kalibrasi), serta sinkronisasi sensor dan pencahayaan. Semua fitur tersebut memerlukan pengujian ulang pada hardware dan PC tujuan.
