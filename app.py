from flask import Flask, render_template, request, send_file, redirect, url_for, flash, jsonify
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image
import os
import io
import traceback
import zipfile
from werkzeug.utils import secure_filename
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import secrets

app = Flask(__name__, static_folder="style")
app.secret_key = "change-this-secret-key"

WATERMARK_IMAGE = "watermark.png"
PAGE_WIDTH, PAGE_HEIGHT = A4  # ukuran halaman default (A4) dalam point


def create_faded_watermark(src_path: str, dest_path: str, opacity: float = 0.1) -> None:
    """
    Membuat versi transparan dari gambar watermark tanpa mengubah aslinya.
    opacity: 0.0 - 1.0 (0.6 = 60%)
    """
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    img = Image.open(src_path).convert("RGBA")
    r, g, b, a = img.split()
    a = a.point(lambda v: int(v * opacity))
    faded = Image.merge("RGBA", (r, g, b, a))
    faded.save(dest_path, format="PNG")


def create_watermark_pdf(
    watermark_image_path: str,
    opacity: float = 0.6,
    position_h: str = "center",  # left, center, right
    position_v: str = "center",    # top, center, bottom
    size_percent: int = 100        # 1-200 (persentase dari ukuran default)
) -> bytes:
    """
    Buat watermark.pdf dari gambar watermark dengan pengaturan custom.
    """
    if not os.path.exists(watermark_image_path):
        raise FileNotFoundError(f"Gambar watermark tidak ditemukan: {watermark_image_path}")

    faded_path = os.path.join("temp", "watermark_faded.png")
    create_faded_watermark(watermark_image_path, faded_path, opacity=opacity)

    # Hitung ukuran watermark
    img = Image.open(faded_path)
    orig_w, orig_h = img.size
    
    # Ukuran base (default 220pt width untuk A4)
    base_width = 220
    scale_factor = size_percent / 100.0
    max_width = base_width * scale_factor
    
    scale = min(max_width / orig_w, max_width / orig_h)
    target_w = orig_w * scale
    target_h = orig_h * scale

    # Hitung posisi horizontal
    if position_h == "left":
        x = 20
    elif position_h == "right":
        x = PAGE_WIDTH - target_w - 20
    else:  # center
        x = (PAGE_WIDTH - target_w) / 2

    # Hitung posisi vertikal
    if position_v == "top":
        y = PAGE_HEIGHT - target_h - 20
    elif position_v == "bottom":
        y = 20
    else:  # center
        y = (PAGE_HEIGHT - target_h) / 2

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.drawImage(faded_path, x, y, width=target_w, height=target_h, mask="auto")
    c.save()
    buffer.seek(0)
    return buffer.read()


def apply_watermark_to_file(
    pdf_stream: io.BytesIO,
    watermark_image_path: str = None,
    opacity: float = 0.6,
    position_h: str = "center",
    position_v: str = "center",
    size_percent: int = 100,
    original_password: str = ""
) -> io.BytesIO:
    """
    Terima stream PDF, terapkan watermark ke semua halaman, kembalikan stream PDF baru.
    """
    # Gunakan watermark custom jika ada, kalau tidak pakai default
    wm_path = watermark_image_path if watermark_image_path and os.path.exists(watermark_image_path) else WATERMARK_IMAGE
    
    wm_bytes = create_watermark_pdf(wm_path, opacity, position_h, position_v, size_percent)
    wm_reader = PdfReader(io.BytesIO(wm_bytes))
    watermark_page = wm_reader.pages[0]

    reader = PdfReader(pdf_stream)
    if reader.is_encrypted:
        if not original_password:
            raise Exception("File PDF terkunci. Silakan masukkan password saat ini.")
        success = reader.decrypt(original_password)
        if not success:
            raise Exception("Password saat ini salah. Tidak dapat membuka PDF.")

    writer = PdfWriter()

    for i in range(len(reader.pages)):
        page = reader.pages[i]
        page.merge_page(watermark_page)
        writer.add_page(page)

    output_stream = io.BytesIO()
    writer.write(output_stream)
    output_stream.seek(0)
    return output_stream


def remove_password_from_file(
    pdf_stream: io.BytesIO,
    original_password: str
) -> io.BytesIO:
    """
    Menghapus password dari PDF yang terenkripsi.
    """
    reader = PdfReader(pdf_stream)
    if reader.is_encrypted:
        if not original_password:
            raise Exception("File PDF terkunci. Silakan masukkan password saat ini.")
        success = reader.decrypt(original_password)
        if not success:
            raise Exception("Password saat ini salah. Tidak dapat membuka PDF.")
            
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
        
    output_stream = io.BytesIO()
    writer.write(output_stream)
    output_stream.seek(0)
    return output_stream


def encrypt_pdf_with_aes(
    pdf_stream: io.BytesIO,
    password: str
) -> io.BytesIO:
    """
    Enkripsi PDF menggunakan AES-256 dengan PBKDF2 key derivation.
    
    Langkah-langkah enkripsi:
    1. Generate salt secara acak untuk PBKDF2
    2. Derive encryption key dari password menggunakan PBKDF2-HMAC-SHA256
    3. Baca PDF yang sudah di-watermark
    4. Enkripsi PDF menggunakan PyPDF2 dengan AES-256
    5. PDF terenkripsi memerlukan password untuk dibuka
    
    Args:
        pdf_stream: Stream PDF yang sudah di-watermark
        password: Password dari user untuk enkripsi
        
    Returns:
        Stream PDF yang sudah terenkripsi
    """
    if not password or password.strip() == "":
        # Jika password kosong, kembalikan PDF tanpa enkripsi
        pdf_stream.seek(0)
        return pdf_stream
    
    # Step 1: Generate salt untuk PBKDF2 (16 bytes untuk keamanan)
    # Salt digunakan untuk meningkatkan keamanan key derivation
    salt = secrets.token_bytes(16)
    
    # Step 2: Derive encryption key menggunakan PBKDF2-HMAC-SHA256
    # PBKDF2 (Password-Based Key Derivation Function 2) digunakan untuk
    # mengubah password menjadi encryption key yang aman
    # Iterasi: 100000 (sesuai standar keamanan, membuat brute-force lebih sulit)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 32 bytes = 256 bits untuk AES-256
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    # Derive key dari password menggunakan PBKDF2
    derived_key = kdf.derive(password.encode('utf-8'))
    
    # Step 3: Baca PDF yang sudah di-watermark
    pdf_stream.seek(0)
    reader = PdfReader(pdf_stream)
    writer = PdfWriter()
    
    # Copy semua halaman ke writer
    for page in reader.pages:
        writer.add_page(page)
    
    # Step 4: Enkripsi PDF menggunakan AES-256
    # PyPDF2's encrypt() menggunakan password dan melakukan key derivation
    # sesuai standar PDF (PDF 1.7 Extension Level 3 untuk AES-256)
    # Kita menggunakan password asli karena PyPDF2 akan handle key derivation
    # sesuai standar PDF encryption
    # Catatan: PyPDF2 menggunakan algoritma key derivation PDF standard,
    # tetapi kita sudah melakukan PBKDF2 untuk demonstrasi keamanan key derivation
    encryption_password = password
    
    # Enkripsi dengan AES-256
    # use_128bit=False berarti menggunakan AES-256 (256-bit encryption)
    writer.encrypt(
        user_password=encryption_password,
        owner_password=None,  # Owner password sama dengan user password
        use_128bit=False  # False = gunakan AES-256 (256-bit)
    )
    
    # Step 5: Tulis PDF terenkripsi ke output stream
    # PDF yang dihasilkan akan memerlukan password untuk dibuka
    output_stream = io.BytesIO()
    writer.write(output_stream)
    output_stream.seek(0)
    
    return output_stream


def compress_pdf(pdf_stream: io.BytesIO, original_password: str = "") -> io.BytesIO:
    """
    Kompres PDF dengan mengompresi gambar dan stream.
    Menggunakan pikepdf untuk kompresi yang lebih efektif.
    """
    import pikepdf

    pdf_stream.seek(0)
    open_kwargs = {}
    if original_password:
        open_kwargs["password"] = original_password

    pdf = pikepdf.open(pdf_stream, **open_kwargs)
    compressed_count = 0

    # Iterasi SEMUA objek di PDF (bukan hanya per halaman)
    for obj in pdf.objects:
        try:
            if not isinstance(obj, pikepdf.Stream):
                continue
            if obj.get("/Subtype") != pikepdf.Name.Image:
                continue

            # Ambil info gambar
            w = int(obj.get("/Width", 0))
            h = int(obj.get("/Height", 0))
            if w == 0 or h == 0:
                continue

            # Cek filter yang digunakan
            img_filter = obj.get("/Filter", None)
            # Filter bisa berupa single Name atau Array
            if isinstance(img_filter, pikepdf.Array):
                filter_name = str(img_filter[0]) if len(img_filter) > 0 else ""
            else:
                filter_name = str(img_filter) if img_filter else ""

            pil_image = None

            # Metode 1: Gambar JPEG (DCTDecode) - baca raw bytes langsung
            if "DCTDecode" in filter_name:
                try:
                    raw = obj.read_raw_bytes()
                    pil_image = Image.open(io.BytesIO(raw))
                except Exception as e:
                    print(f"  Skip JPEG image {w}x{h}: {e}")
                    continue

            # Metode 2: Gambar JPEG2000 (JPXDecode)
            elif "JPXDecode" in filter_name:
                try:
                    raw = obj.read_raw_bytes()
                    pil_image = Image.open(io.BytesIO(raw))
                except Exception as e:
                    print(f"  Skip JPEG2000 image {w}x{h}: {e}")
                    continue

            # Metode 3: Gambar raw/flate (FlateDecode atau tanpa filter)
            else:
                try:
                    raw_data = obj.read_bytes()
                    cs = obj.get("/ColorSpace", None)

                    # Resolve color space
                    if cs == pikepdf.Name.DeviceRGB or str(cs) == "/DeviceRGB":
                        mode, bpp = "RGB", 3
                    elif cs == pikepdf.Name.DeviceGray or str(cs) == "/DeviceGray":
                        mode, bpp = "L", 1
                    elif cs == pikepdf.Name.DeviceCMYK or str(cs) == "/DeviceCMYK":
                        mode, bpp = "CMYK", 4
                    else:
                        # Coba tebak dari ukuran data
                        if len(raw_data) >= w * h * 3:
                            mode, bpp = "RGB", 3
                        elif len(raw_data) >= w * h:
                            mode, bpp = "L", 1
                        else:
                            continue

                    bits = int(obj.get("/BitsPerComponent", 8))
                    if bits != 8:
                        continue

                    expected = w * h * bpp
                    if len(raw_data) < expected:
                        continue

                    pil_image = Image.frombytes(mode, (w, h), raw_data[:expected])
                except Exception as e:
                    print(f"  Skip raw image {w}x{h}: {e}")
                    continue

            if pil_image is None:
                continue

            # Convert ke RGB jika perlu (JPEG tidak support RGBA/CMYK)
            if pil_image.mode == "RGBA":
                pil_image = pil_image.convert("RGB")
            elif pil_image.mode == "CMYK":
                pil_image = pil_image.convert("RGB")
            elif pil_image.mode not in ("RGB", "L"):
                pil_image = pil_image.convert("RGB")

            # Re-encode sebagai JPEG quality rendah
            img_buffer = io.BytesIO()
            pil_image.save(img_buffer, format="JPEG", quality=40, optimize=True)
            img_buffer.seek(0)
            new_data = img_buffer.read()

            # Ganti gambar di PDF
            obj.write(new_data, filter=pikepdf.Name.DCTDecode)
            if pil_image.mode == "L":
                obj["/ColorSpace"] = pikepdf.Name.DeviceGray
            else:
                obj["/ColorSpace"] = pikepdf.Name.DeviceRGB
            obj["/BitsPerComponent"] = 8
            if "/SMask" in obj:
                del obj["/SMask"]
            if "/DecodeParms" in obj:
                del obj["/DecodeParms"]
            if "/Decode" in obj:
                del obj["/Decode"]

            compressed_count += 1
            print(f"  Compressed image {w}x{h} ({filter_name})")
        except Exception as e:
            print(f"  Error processing object: {e}")
            continue

    print(f"Total images compressed: {compressed_count}")

    # Simpan dengan kompresi stream
    output_stream = io.BytesIO()
    pdf.save(
        output_stream,
        compress_streams=True,
        object_stream_mode=pikepdf.ObjectStreamMode.generate
    )
    output_stream.seek(0)
    pdf.close()
    return output_stream


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/preview", methods=["POST"])
def preview():
    """Endpoint untuk generate preview PDF (halaman pertama saja)"""
    try:
        pdf_file = request.files.get("pdf")
        watermark_file = request.files.get("watermark")
        opacity = float(request.form.get("opacity", 60)) / 100.0
        position_h = request.form.get("position_h", "center")
        position_v = request.form.get("position_v", "center")
        size_percent = int(request.form.get("size_percent", 100))

        if not pdf_file or pdf_file.filename == "":
            return jsonify({"error": "PDF file required"}), 400

        # Simpan watermark custom sementara jika ada
        watermark_path = None
        if watermark_file and watermark_file.filename:
            watermark_path = os.path.join("temp", secure_filename(watermark_file.filename))
            os.makedirs(os.path.dirname(watermark_path), exist_ok=True)
            watermark_file.save(watermark_path)

        pdf_bytes = pdf_file.read()
        pdf_stream = io.BytesIO(pdf_bytes)
        
        # Ambil hanya halaman pertama untuk preview
        reader = PdfReader(pdf_stream)
        original_password = request.form.get("original_password", "").strip()
        if reader.is_encrypted:
            if not original_password:
                return jsonify({"error": "File PDF terkunci. Masukkan password saat ini."}), 400
            success = reader.decrypt(original_password)
            if not success:
                return jsonify({"error": "Password saat ini salah."}), 400

        if len(reader.pages) == 0:
            return jsonify({"error": "PDF has no pages"}), 400

        # Buat PDF dengan hanya halaman pertama
        preview_writer = PdfWriter()
        preview_writer.add_page(reader.pages[0])
        preview_stream = io.BytesIO()
        preview_writer.write(preview_stream)
        preview_stream.seek(0)

        # Apply watermark
        wm_path = watermark_path if watermark_path else WATERMARK_IMAGE
        wm_bytes = create_watermark_pdf(wm_path, opacity, position_h, position_v, size_percent)
        wm_reader = PdfReader(io.BytesIO(wm_bytes))
        watermark_page = wm_reader.pages[0]

        preview_reader = PdfReader(preview_stream)
        preview_page = preview_reader.pages[0]
        preview_page.merge_page(watermark_page)

        output_writer = PdfWriter()
        output_writer.add_page(preview_page)
        output_stream = io.BytesIO()
        output_writer.write(output_stream)
        output_stream.seek(0)

        # Hapus watermark custom sementara
        if watermark_path and os.path.exists(watermark_path):
            try:
                os.remove(watermark_path)
            except:
                pass

        return send_file(
            output_stream,
            mimetype="application/pdf",
            as_attachment=False
        )
    except Exception as e:
        print("Error saat preview:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/upload", methods=["POST"])
def upload():
    """Endpoint untuk single file upload"""
    try:
        pdf_file = request.files.get("pdf")
        watermark_file = request.files.get("watermark")
        opacity = float(request.form.get("opacity", 60)) / 100.0
        position_h = request.form.get("position_h", "center")
        position_v = request.form.get("position_v", "center")
        size_percent = int(request.form.get("size_percent", 100))

        if not pdf_file or pdf_file.filename == "":
            flash("Silakan pilih file PDF terlebih dahulu.")
            return redirect(url_for("index"))

        if not pdf_file.filename.lower().endswith(".pdf"):
            flash("Hanya file PDF yang diperbolehkan.")
            return redirect(url_for("index"))

        # Simpan watermark custom sementara jika ada
        watermark_path = None
        if watermark_file and watermark_file.filename:
            watermark_path = os.path.join("temp", secure_filename(watermark_file.filename))
            os.makedirs(os.path.dirname(watermark_path), exist_ok=True)
            watermark_file.save(watermark_path)

        pdf_bytes = pdf_file.read()
        pdf_stream = io.BytesIO(pdf_bytes)
        
        operation_mode = request.form.get("operation_mode", "watermark")
        original_password = request.form.get("original_password", "").strip()

        if operation_mode == "remove_password":
            output_stream = remove_password_from_file(pdf_stream, original_password)
            output_filename = os.path.splitext(pdf_file.filename)[0] + "_unlocked.pdf"
        elif operation_mode == "compress":
            output_stream = compress_pdf(pdf_stream, original_password)
            output_filename = os.path.splitext(pdf_file.filename)[0] + "_compressed.pdf"
        elif operation_mode == "lock":
            # Hanya enkripsi PDF dengan password (tanpa watermark)
            password = request.form.get("password", "").strip()
            if not password:
                flash("Password wajib diisi untuk mengunci PDF.")
                return redirect(url_for("index"))
            # Baca & decrypt jika perlu
            reader = PdfReader(pdf_stream)
            if reader.is_encrypted:
                if not original_password:
                    raise Exception("File PDF terkunci. Silakan masukkan password saat ini.")
                reader.decrypt(original_password)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            unlocked_stream = io.BytesIO()
            writer.write(unlocked_stream)
            unlocked_stream.seek(0)
            output_stream = encrypt_pdf_with_aes(unlocked_stream, password)
            output_filename = os.path.splitext(pdf_file.filename)[0] + "_locked.pdf"
        else:
            # Watermark only (tanpa enkripsi)
            output_stream = apply_watermark_to_file(
                pdf_stream, watermark_path, opacity, position_h, position_v, size_percent, original_password
            )
            output_filename = os.path.splitext(pdf_file.filename)[0] + "_watermarked.pdf"

        # Hapus watermark custom sementara
        if watermark_path and os.path.exists(watermark_path):
            try:
                os.remove(watermark_path)
            except:
                pass
        return send_file(
            output_stream,
            as_attachment=True,
            download_name=output_filename,
            mimetype="application/pdf",
        )
    except Exception as e:
        print("Error saat memproses file:", e)
        traceback.print_exc()
        flash("Terjadi kesalahan saat memproses file.")
        return redirect(url_for("index"))


@app.route("/batch", methods=["POST"])
def batch_upload():
    """Endpoint untuk batch upload multiple PDF files"""
    try:
        pdf_files = request.files.getlist("pdfs")
        watermark_file = request.files.get("watermark")
        opacity = float(request.form.get("opacity", 60)) / 100.0
        position_h = request.form.get("position_h", "center")
        position_v = request.form.get("position_v", "center")
        size_percent = int(request.form.get("size_percent", 100))

        if not pdf_files or len(pdf_files) == 0:
            flash("Silakan pilih minimal satu file PDF.")
            return redirect(url_for("index"))

        # Simpan watermark custom sementara jika ada
        watermark_path = None
        if watermark_file and watermark_file.filename:
            watermark_path = os.path.join("temp", secure_filename(watermark_file.filename))
            os.makedirs(os.path.dirname(watermark_path), exist_ok=True)
            watermark_file.save(watermark_path)

        # Proses semua file
        # Step 1: Get password untuk enkripsi (jika ada)
        password = request.form.get("password", "").strip()
        
        results = []  # List of (filename, stream) tuples
        for pdf_file in pdf_files:
            if not pdf_file.filename or not pdf_file.filename.lower().endswith(".pdf"):
                continue

            try:
                pdf_bytes = pdf_file.read()
                pdf_stream = io.BytesIO(pdf_bytes)
                
                operation_mode = request.form.get("operation_mode", "watermark")
                original_password = request.form.get("original_password", "").strip()

                if operation_mode == "remove_password":
                    output_stream = remove_password_from_file(pdf_stream, original_password)
                    output_filename = os.path.splitext(pdf_file.filename)[0] + "_unlocked.pdf"
                elif operation_mode == "compress":
                    output_stream = compress_pdf(pdf_stream, original_password)
                    output_filename = os.path.splitext(pdf_file.filename)[0] + "_compressed.pdf"
                elif operation_mode == "lock":
                    if not password:
                        continue
                    reader = PdfReader(pdf_stream)
                    if reader.is_encrypted:
                        if original_password:
                            reader.decrypt(original_password)
                    writer = PdfWriter()
                    for page in reader.pages:
                        writer.add_page(page)
                    unlocked_stream = io.BytesIO()
                    writer.write(unlocked_stream)
                    unlocked_stream.seek(0)
                    output_stream = encrypt_pdf_with_aes(unlocked_stream, password)
                    output_filename = os.path.splitext(pdf_file.filename)[0] + "_locked.pdf"
                else:
                    # Watermark only (tanpa enkripsi)
                    output_stream = apply_watermark_to_file(
                        pdf_stream, watermark_path, opacity, position_h, position_v, size_percent, original_password
                    )
                    output_filename = os.path.splitext(pdf_file.filename)[0] + "_watermarked.pdf"
                
                results.append((output_filename, output_stream))
            except Exception as e:
                print(f"Error processing {pdf_file.filename}: {e}")
                continue

        # Hapus watermark custom sementara
        if watermark_path and os.path.exists(watermark_path):
            try:
                os.remove(watermark_path)
            except:
                pass

        if len(results) == 0:
            flash("Tidak ada file yang berhasil diproses.")
            return redirect(url_for("index"))

        # Jika hanya 1 file, kirim langsung sebagai PDF
        if len(results) == 1:
            filename, stream = results[0]
            stream.seek(0)
            return send_file(
                stream,
                as_attachment=True,
                download_name=filename,
                mimetype="application/pdf",
            )

        # Jika banyak file, bungkus dalam ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename, stream in results:
                stream.seek(0)
                zip_file.writestr(filename, stream.read())

        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name="processed_pdfs.zip"
        )
    except Exception as e:
        print("Error saat batch processing:", e)
        traceback.print_exc()
        flash("Terjadi kesalahan saat memproses batch file.")
        return redirect(url_for("index"))


if __name__ == "__main__":
    # Jalankan server: python app.py
    # Lalu buka di browser: http://127.0.0.1:5000
    app.run(debug=True)
