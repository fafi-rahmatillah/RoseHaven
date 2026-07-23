# RoseHaven Hotel - Aplikasi Reservasi Django

Aplikasi web reservasi hotel bintang 4 dengan tiga Django app hasil `startapp`:

- `administrator` — akses penuh, CRUD, akun, pembayaran, laporan, dan pengaturan hotel.
- `resepsionis` — reservasi datang langsung, verifikasi pembayaran, check in, check out, dan jadwal reservasi.
- `customer` — registrasi, login, profil, daftar/detail kamar, reservasi, upload pembayaran, pembatalan, riwayat.

## Menjalankan di Windows

1. Buka folder proyek di terminal/Command Prompt.
2. Cara termudah: klik dua kali `INSTALL_DAN_JALANKAN.bat`. File ini otomatis membuat virtual environment dan memasang Django dan Pillow jika belum tersedia.
3. Alternatif: jalankan `setup_windows.bat` satu kali, lalu `run_windows.bat`.
4. Buka `http://127.0.0.1:8000/`.

## Menjalankan manual

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_rosehaven
python manage.py runserver
```

Database SQLite dan data demo sudah disertakan. Bila ingin membuat ulang data awal, jalankan `python manage.py seed_rosehaven`.

## Akun Demo

| Hak Akses | Username | Password | URL |
|---|---|---|---|
| Administrator | `administrator` | `RoseHaven123!` | `/administrator/` |
| Resepsionis | `resepsionis` | `RoseHaven123!` | `/resepsionis/` |
| Customer | `customer` | `RoseHaven123!` | `/customer/` |

Halaman login umum: `/login/`. Setelah login, sistem otomatis mengarahkan pengguna sesuai hak akses.

> Untuk penggunaan produksi, ganti `SECRET_KEY`, ubah password demo, set `DEBUG=False`, atur `ALLOWED_HOSTS`, dan gunakan server/database produksi.
