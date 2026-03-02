![alt text](https://github.com/Lulyar/pdf-watermark/blob/main/image/Screenshot%202025-12-28%20173014.png?raw=true)

# WatermarkPDFs

Aplikasi web berbasis Python dan Flask untuk mengelola file PDF dengan fitur watermark, kompresi, penghapusan sandi, dan enkripsi.

## Fitur Utama

- Menambahkan Watermark: Menempelkan teks atau gambar watermark pada berkas PDF dengan pengaturan untuk transparansi, posisi vertikal/horizontal, serta ukuran.
- Pemrosesan Banyak File: Mendukung unggah ganda (batch) untuk memproses beberapa file PDF sekaligus. Hasil unduhan akan berformat ZIP.
- Enkripsi PDF: Mengunci file PDF menggunakan password dengan algoritma keamanan enkripsi AES-256 serta PBKDF2.
- Hapus Proteksi: Menghilangkan kata sandi dari file PDF yang terkunci (membutuhkan kata sandi asli).
- Kompresi PDF: Membantu mengecilkan ukuran data PDF dengan menurunkan kualitas gambar di dalamnya secara otomatis.
- Pratinjau Watermark: Memeriksa bentuk pratinjau watermark pada halaman pertama secara instan sebelum diterapkan pada keseluruhan dokumen.

## Persyaratan Sistem

Aplikasi ini membutuhkan Python dan beberapa pustaka utama. Semua pustaka ada di dalam file persyaratan.

Untuk melakukan instalasi secara otomatis, buka terminal dan jalankan:
```bash
pip install -r requirements.txt
```

## Cara Menjalankan

1. Buka command prompt atau terminal.
2. Masuk ke lokasi tempat proyek ini berada.
3. Jalankan berkas utama melalui perintah berikut:
```bash
python app.py
```
4. Setelah server aktif, buka browser favorit Anda.
5. Kunjungi alamat lokal ini:
```text
http://127.0.0.1:5000
```

## Struktur Berkas

- app.py: Berisi jalur rute Flask dan semua kode fungsi proses pengelolaan PDF.
- templates/: Memuat file antarmuka utama (index.html).
- style/: Memuat fail statis gaya CSS maupun kode JavaScript.
- temp/: Lokasi penyimpanan temporer untuk gambar yang diolah.
- requirements.txt: Berkas daftar pustaka spesifik Python.
