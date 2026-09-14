"""Membuat berkas fixture Surat Tugas untuk pengujian ocr-engine.

Dijalankan manual, bukan bagian dari test run:
    python tests/fixtures/generate_fixtures.py tests/fixtures

Keluarannya deterministik (seed tetap), sehingga regenerasi pada mesin yang sama
menghasilkan berkas identik.

PENTING - berkas hasil generator ini TETAP di-commit, jangan di-gitignore.
Skrip ini membutuhkan Times New Roman dari C:\\Windows\\Fonts, jadi tidak dapat
dijalankan di CI Linux. Fixture yang ter-commit adalah satu-satunya baseline yang
dipakai bersama; skrip ini ada untuk menerangkan asal-usulnya dan memudahkan
pembuatan varian baru, bukan untuk membuat ulang saat pengujian.

Isi dokumen mengikuti field di documents/tech/extraction-schema.md. Semuanya
fiktif: nama, NIP, dan nomor surat dikarang untuk keperluan uji.

Catatan: fixture ini menutup jalur kode dan mengunci regresi. Ia BUKAN pengukur
akurasi sistem - hanya satu tata letak, satu font, tanpa stempel, kop berlogo,
kertas menguning, atau tulisan tangan. Angka akurasi yang sahih hanya bisa
diperoleh dari dokumen asli (OQ-1).
"""
import os
import sys

import cv2
import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFont

FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
A4_150DPI = (1240, 1754)  # lebar x tinggi

KOP = [
    ("timesbd.ttf", 30, "KEMENTERIAN KEUANGAN REPUBLIK INDONESIA"),
    ("timesbd.ttf", 26, "DIREKTORAT JENDERAL PERBENDAHARAAN"),
    ("times.ttf", 20, "Jalan Lapangan Banteng Timur Nomor 2-4, Jakarta Pusat 10710"),
    ("times.ttf", 20, "Telepon (021) 3449230; Faksimile (021) 3865937"),
]

BADAN = [
    (60, "SURAT TUGAS", "timesbd.ttf", 32, "center"),
    (8, "Nomor: 090/ST/IX/2026", "times.ttf", 24, "center"),
    (46, "Dasar        : Surat Undangan Nomor UND-45/PB.1/2026 tanggal", "times.ttf", 23, "left"),
    (4, "               1 September 2026 perihal Rapat Koordinasi.", "times.ttf", 23, "left"),
    (30, "Menugaskan kepada:", "times.ttf", 23, "left"),
    (26, "1.  Nama                     : Budi Santoso", "times.ttf", 23, "left"),
    (6, "     NIP                        : 198503122010011004", "times.ttf", 23, "left"),
    (6, "     Pangkat/Golongan  : Penata Muda Tingkat I / III-b", "times.ttf", 23, "left"),
    (6, "     Jabatan                  : Analis Perbendaharaan", "times.ttf", 23, "left"),
    (20, "2.  Nama                     : Siti Rahayu", "times.ttf", 23, "left"),
    (6, "     NIP                        : 199007152015022003", "times.ttf", 23, "left"),
    (6, "     Pangkat/Golongan  : Penata / III-c", "times.ttf", 23, "left"),
    (6, "     Jabatan                  : Pelaksana Verifikasi", "times.ttf", 23, "left"),
    (32, "Maksud Perjalanan  : Rapat Koordinasi Penyusunan Laporan Keuangan", "times.ttf", 23, "left"),
    (6, "Tempat Tujuan          : SURABAYA", "times.ttf", 23, "left"),
    (6, "Alat Angkut               : Pesawat Udara", "times.ttf", 23, "left"),
    (6, "Tanggal Berangkat    : 15 September 2026", "times.ttf", 23, "left"),
    (6, "Tanggal Kembali        : 18 September 2026", "times.ttf", 23, "left"),
    (6, "Lama Perjalanan       : 4 (empat) hari", "times.ttf", 23, "left"),
    (6, "Pembebanan Anggaran : DIPA Ditjen Perbendaharaan TA 2026", "times.ttf", 23, "left"),
    (36, "Demikian surat tugas ini dibuat untuk dilaksanakan dengan penuh", "times.ttf", 23, "left"),
    (4, "tanggung jawab.", "times.ttf", 23, "left"),
]

PENUTUP = [
    (0, "Jakarta, 10 September 2026", "times.ttf", 23),
    (6, "Pejabat Pembuat Komitmen,", "times.ttf", 23),
    (120, "Dr. Ahmad Hidayat, M.M.", "timesbd.ttf", 23),
    (6, "NIP 197204101998031002", "times.ttf", 23),
]

HALAMAN2 = [
    (60, "LAMPIRAN SURAT TUGAS", "timesbd.ttf", 28, "center"),
    (8, "Nomor: 090/ST/IX/2026", "times.ttf", 23, "center"),
    (50, "Rincian Biaya Perjalanan Dinas", "timesbd.ttf", 24, "left"),
    (30, "1.  Tiket pesawat Jakarta - Surabaya PP     : Rp 2.400.000", "times.ttf", 23, "left"),
    (8, "2.  Uang harian 4 hari x Rp 430.000            : Rp 1.720.000", "times.ttf", 23, "left"),
    (8, "3.  Penginapan 3 malam x Rp 650.000        : Rp 1.950.000", "times.ttf", 23, "left"),
    (8, "4.  Transportasi lokal                                  : Rp    300.000", "times.ttf", 23, "left"),
    (16, "     Jumlah                                                 : Rp 6.370.000", "timesbd.ttf", 23, "left"),
    (30, "Terbilang: enam juta tiga ratus tujuh puluh ribu rupiah.", "times.ttf", 23, "left"),
]


def _font(nama, ukuran):
    # Layout BASIC dikunci. Tanpa ini Pillow otomatis memakai RAQM begitu menemukan
    # libfribidi/libharfbuzz di PATH - dan installer Tesseract membawa keduanya.
    # RAQM menggeser posisi huruf 1-2 px, sehingga fixture berubah hanya karena
    # isi PATH berubah, padahal kodenya sama.
    return ImageFont.truetype(os.path.join(FONTS, nama), ukuran,
                              layout_engine=ImageFont.Layout.BASIC)


def _tulis(draw, x, y, teks, font, align, lebar):
    if align == "center":
        w = draw.textbbox((0, 0), teks, font=font)[2]
        x = (lebar - w) // 2
    draw.text((x, y), teks, fill=(0, 0, 0), font=font)


def halaman_utama():
    img = Image.new("RGB", A4_150DPI, (255, 255, 255))
    d = ImageDraw.Draw(img)
    lebar, tinggi = A4_150DPI
    margin = 110

    y = 70
    for nama_font, ukuran, teks in KOP:
        f = _font(nama_font, ukuran)
        _tulis(d, margin, y, teks, f, "center", lebar)
        y += ukuran + 8

    y += 14
    d.line([(margin, y), (lebar - margin, y)], fill=(0, 0, 0), width=4)

    for jarak, teks, nama_font, ukuran, align in BADAN:
        y += jarak
        _tulis(d, margin, y, teks, _font(nama_font, ukuran), align, lebar)
        y += ukuran

    y += 50
    x_ttd = lebar - margin - 420
    for jarak, teks, nama_font, ukuran in PENUTUP:
        y += jarak
        d.text((x_ttd, y), teks, fill=(0, 0, 0), font=_font(nama_font, ukuran))
        y += ukuran

    return np.array(img)[:, :, ::-1].copy()  # RGB -> BGR


def halaman_lampiran():
    img = Image.new("RGB", A4_150DPI, (255, 255, 255))
    d = ImageDraw.Draw(img)
    lebar, _ = A4_150DPI
    margin = 110
    y = 90
    for jarak, teks, nama_font, ukuran, align in HALAMAN2:
        y += jarak
        _tulis(d, margin, y, teks, _font(nama_font, ukuran), align, lebar)
        y += ukuran
    return np.array(img)[:, :, ::-1].copy()


def jadikan_foto(bgr, rng, kekuatan=1.0):
    """Meniru hasil jepretan kamera HP: perspektif, bayangan, derau, blur ringan."""
    # Foto HP yang sudah dikompresi klien tetap sekitar 1600-2000 px pada sisi
    # panjang (PRD: maksimal 10 MB setelah kompresi). Mengecilkan lebih jauh
    # membuang informasi yang tidak pernah hilang pada masukan sungguhan.
    h, w = bgr.shape[:2]
    skala = 1800 / max(h, w)
    kecil = cv2.resize(bgr, (int(w * skala), int(h * skala)), interpolation=cv2.INTER_AREA)
    kh, kw = kecil.shape[:2]

    kanvas_w, kanvas_h = int(kw * 1.35), int(kh * 1.25)
    meja = np.full((kanvas_h, kanvas_w, 3), (72, 84, 96), dtype=np.uint8)
    meja = cv2.add(meja, rng.integers(0, 22, meja.shape, dtype=np.uint8))

    m = int(min(kanvas_w, kanvas_h) * 0.06)
    g = kekuatan
    src = np.float32([[0, 0], [kw, 0], [kw, kh], [0, kh]])
    dst = np.float32([
        [m + 26 * g,               m + 10 * g],
        [kanvas_w - m - 8 * g,     m + 40 * g],
        [kanvas_w - m - 30 * g,    kanvas_h - m - 12 * g],
        [m + 6 * g,                kanvas_h - m - 34 * g],
    ])
    cv2.warpPerspective(kecil, cv2.getPerspectiveTransform(src, dst),
                        (kanvas_w, kanvas_h), meja, borderMode=cv2.BORDER_TRANSPARENT)

    # gradien bayangan dari kiri atas
    yy, xx = np.mgrid[0:kanvas_h, 0:kanvas_w].astype(np.float32)
    bayang = 0.62 + 0.38 * (xx / kanvas_w * 0.6 + yy / kanvas_h * 0.4)
    meja = np.clip(meja * bayang[:, :, None], 0, 255).astype(np.uint8)

    meja = cv2.GaussianBlur(meja, (3, 3), 0)
    derau = rng.normal(0, 4.5, meja.shape)
    return np.clip(meja.astype(np.float32) + derau, 0, 255).astype(np.uint8)


def miringkan(bgr, derajat):
    h, w = bgr.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), derajat, 1.0)
    return cv2.warpAffine(bgr, M, (w, h), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


def _medan_halus(rng, h, w, sel, sigma):
    """Medan acak halus bernilai rata-rata 0, simpangan baku 1.

    Dibangkitkan pada grid kasar (satu nilai per `sel` piksel), diperbesar, lalu
    dihaluskan - menghasilkan variasi bergelombang, bukan derau per piksel.
    """
    kasar = rng.standard_normal((max(2, h // sel), max(2, w // sel))).astype(np.float32)
    medan = cv2.resize(kasar, (w, h), interpolation=cv2.INTER_CUBIC)
    medan = cv2.GaussianBlur(medan, (0, 0), sigma)
    medan -= medan.mean()
    return medan / (medan.std() + 1e-6)


def jadikan_lecek(bgr, rng, kekuatan=1.0):
    """Meniru kertas yang pernah diremas lalu diratakan kembali dan dipindai.

    Kertas dimodelkan sebagai peta ketinggian: gelombang lebar ditambah garis
    lipatan tajam. Dari peta itu diturunkan dua efek yang terlihat pada kertas
    lecek sungguhan - baris teks yang bengkok (distorsi geometri) dan pola
    terang-gelap di sekitar lipatan (bayangan dari sudut cahaya pemindai).
    """
    h, w = bgr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    tinggi = _medan_halus(rng, h, w, 70, 22) * 5.0 * kekuatan
    garis_gelap = np.zeros((h, w), np.float32)

    for _ in range(int(round(4 + 3 * kekuatan))):
        cx, cy = rng.uniform(0.05 * w, 0.95 * w), rng.uniform(0.05 * h, 0.95 * h)
        sudut = rng.uniform(0, np.pi)
        tx, ty = np.cos(sudut), np.sin(sudut)
        jarak = (xx - cx) * -ty + (yy - cy) * tx      # tegak lurus garis lipatan
        sepanjang = (xx - cx) * tx + (yy - cy) * ty   # sejajar garis lipatan
        panjang = rng.uniform(0.25, 0.8) * max(h, w)
        redam = np.exp(-(sepanjang / panjang) ** 2)  # lipatan memudar di ujungnya

        arah = rng.choice([-1.0, 1.0])  # lipatan gunung atau lembah
        tinggi += arah * 6.0 * kekuatan * np.exp(-np.abs(jarak) / rng.uniform(20, 50)) * redam
        garis_gelap = np.maximum(
            garis_gelap, np.exp(-np.abs(jarak) / 1.5) * redam * rng.uniform(0.4, 1.0))

    gy, gx = np.gradient(tinggi)

    # distorsi geometri: permukaan yang miring menggeser posisi tinta. Gradien
    # dihaluskan dulu supaya baris teks melengkung melewati lipatan, bukan patah -
    # kertas yang diratakan kembali tidak pernah memotong hurufnya.
    geser = 9.0
    map_x = xx + cv2.GaussianBlur(gx, (0, 0), 5) * geser
    map_y = yy + cv2.GaussianBlur(gy, (0, 0), 5) * geser
    bengkok = cv2.remap(bgr, map_x, map_y, interpolation=cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_REPLICATE).astype(np.float32)

    # bayangan: cahaya pemindai datang dari arah kiri atas. Kontrasnya sengaja
    # rendah - pemindai flatbed menekan kertas rata, jadi bayangannya lembut.
    cahaya = 1.0 - 0.35 * (gx * 0.7 + gy * 0.7)
    cahaya *= 1.0 - 0.18 * kekuatan * garis_gelap   # retakan serat tepat di puncak lipatan
    cahaya = np.clip(cahaya, 0.70, 1.06)

    hasil = bengkok * cahaya[:, :, None]
    hasil += rng.normal(0, 3.0, hasil.shape)
    return np.clip(hasil, 0, 255).astype(np.uint8)


def jadikan_luntur(bgr, rng, noda, kekuatan=1.0):
    """Meniru dokumen yang pernah basah: tinta melebar, memudar, dan meleleh ke bawah.

    `noda` adalah daftar (x, y, jari_jari) dalam pecahan lebar/tinggi halaman,
    sengaja ditempatkan di atas field penting agar ujinya bermakna.
    """
    h, w = bgr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    tinta = (255.0 - gray) / 255.0   # 1 = tinta pekat, 0 = kertas polos

    # masker noda air dengan batas tak beraturan
    masker = np.zeros((h, w), np.float32)
    for fx, fy, fr in noda:
        cx, cy, r = fx * w, fy * h, fr * w
        rx, ry = r * rng.uniform(0.8, 1.2), r * rng.uniform(0.7, 1.1)
        # batas bergelombang lebar ditambah sedikit riak halus - hanya riak halus
        # saja menghasilkan "tentakel" dan pulau-pulau kecil yang tidak wajar
        acak = (0.16 * _medan_halus(rng, h, w, 110, 35)
                + 0.04 * _medan_halus(rng, h, w, 30, 8))
        jarak = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) + acak
        masker = np.maximum(masker, (jarak < 1.0).astype(np.float32))

    tepi_noda = cv2.morphologyEx(masker, cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8))
    tepi_noda = cv2.GaussianBlur(tepi_noda, (0, 0), 1.6)
    masker = cv2.GaussianBlur(masker, (0, 0), 5)

    # tinta melebar ke segala arah, dan meleleh ke bawah mengikuti aliran air
    melebar = cv2.GaussianBlur(tinta, (0, 0), 1.0 + 0.9 * kekuatan)
    k = int(5 + 6 * kekuatan) | 1
    kernel = np.zeros((k, k), np.float32)
    kernel[k // 2:, k // 2] = 1.0            # hanya separuh bawah: tinta turun, tidak naik
    kernel /= kernel.sum()
    meleleh = cv2.filter2D(tinta, -1, kernel, anchor=(k // 2, k // 2))
    tinta_basah = np.clip((0.55 * melebar + 0.45 * meleleh) * 1.25, 0, 1)

    # tingkat pudar tidak rata di dalam noda - bagian yang lebih lama basah lebih luntur.
    # Batas atas 0.85 menjaga teks tetap samar terlihat mata manusia pada kategori berat.
    pudar = min(0.7, 0.35 * kekuatan)
    peta_pudar = np.clip(pudar * (1.0 + 0.3 * _medan_halus(rng, h, w, 80, 25)), 0, 0.85)
    tinta_basah *= 1.0 - peta_pudar
    tinta_akhir = tinta * (1.0 - masker) + tinta_basah * masker

    # warna kertas: sedikit menguning, kecokelatan tak rata di dalam noda,
    # dan garis tipis lebih gelap di tepi tempat air terakhir mengering
    kertas = np.array([236, 243, 247], np.float32)      # BGR, putih kekuningan
    noda_warna = np.array([168, 196, 212], np.float32)
    tepi_warna = np.array([118, 150, 172], np.float32)
    rona = (0.25 + 0.15 * np.clip(_medan_halus(rng, h, w, 80, 25), -1.5, 1.5) / 1.5)
    rona = (rona * masker)[:, :, None]
    dasar = kertas * (1 - rona) + noda_warna * rona
    bobot_tepi = np.clip(tepi_noda * 0.55 * kekuatan, 0, 0.55)[:, :, None]
    dasar = dasar * (1 - bobot_tepi) + tepi_warna * bobot_tepi

    warna_tinta = np.array([48, 34, 30], np.float32)   # hitam kebiruan
    hasil = dasar * (1 - tinta_akhir[:, :, None]) + warna_tinta * tinta_akhir[:, :, None]
    hasil += rng.normal(0, 2.5, hasil.shape)
    return np.clip(hasil, 0, 255).astype(np.uint8)


def pdf_dari_gambar(halaman_bgr, tujuan):
    """PDF berisi gambar saja - tanpa text layer, memaksa jalur OCR."""
    doc = pymupdf.open()
    for bgr in halaman_bgr:
        # JPEG, seperti keluaran mesin pemindai sungguhan - PNG membuat berkas 20x lebih besar
        ok, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
        assert ok
        page = doc.new_page(width=595, height=842)  # A4 dalam poin
        page.insert_image(pymupdf.Rect(0, 0, 595, 842), stream=buf.tobytes())
    doc.save(tujuan)
    doc.close()


def main(tujuan):
    os.makedirs(tujuan, exist_ok=True)
    rng = np.random.default_rng(20260910)

    utama = halaman_utama()
    lampiran = halaman_lampiran()

    berkas = []

    p = os.path.join(tujuan, "surat_tugas_scan.png")
    cv2.imwrite(p, utama)
    berkas.append(p)

    p = os.path.join(tujuan, "surat_tugas_miring.png")
    cv2.imwrite(p, miringkan(utama, -8.0))
    berkas.append(p)

    p = os.path.join(tujuan, "surat_tugas_foto.jpg")
    cv2.imwrite(p, jadikan_foto(utama, rng, 1.0), [cv2.IMWRITE_JPEG_QUALITY, 82])
    berkas.append(p)

    p = os.path.join(tujuan, "surat_tugas_foto_sulit.jpg")
    cv2.imwrite(p, jadikan_foto(utama, rng, 2.2), [cv2.IMWRITE_JPEG_QUALITY, 68])
    berkas.append(p)

    p = os.path.join(tujuan, "surat_tugas_scan.pdf")
    pdf_dari_gambar([utama], p)
    berkas.append(p)

    p = os.path.join(tujuan, "surat_tugas_2halaman.pdf")
    pdf_dari_gambar([utama, lampiran], p)
    berkas.append(p)

    # Dokumen rusak memakai seed sendiri: menambah atau mengubah varian di bawah
    # tidak boleh menggeser keluaran fixture di atas yang sudah dipakai tes.
    p = os.path.join(tujuan, "surat_tugas_lecek.jpg")
    cv2.imwrite(p, jadikan_lecek(utama, np.random.default_rng(1001), 1.0),
                [cv2.IMWRITE_JPEG_QUALITY, 85])
    berkas.append(p)

    p = os.path.join(tujuan, "surat_tugas_lecek_berat.jpg")
    cv2.imwrite(p, jadikan_lecek(utama, np.random.default_rng(1002), 2.0),
                [cv2.IMWRITE_JPEG_QUALITY, 85])
    berkas.append(p)

    # Posisi noda dalam pecahan halaman, dihitung dari tata letak halaman_utama:
    # nomor surat ~y 0.18, NIP Budi ~0.31, NIP Siti ~0.39, SURABAYA ~0.47.
    p = os.path.join(tujuan, "surat_tugas_luntur.jpg")
    noda_ringan = [(0.52, 0.19, 0.09), (0.36, 0.40, 0.11)]
    cv2.imwrite(p, jadikan_luntur(utama, np.random.default_rng(2001), noda_ringan, 1.0),
                [cv2.IMWRITE_JPEG_QUALITY, 85])
    berkas.append(p)

    p = os.path.join(tujuan, "surat_tugas_luntur_berat.jpg")
    noda_berat = [(0.55, 0.17, 0.11), (0.38, 0.36, 0.18), (0.30, 0.50, 0.12)]
    cv2.imwrite(p, jadikan_luntur(utama, np.random.default_rng(2002), noda_berat, 1.8),
                [cv2.IMWRITE_JPEG_QUALITY, 85])
    berkas.append(p)

    for b in berkas:
        print(f"  {os.path.basename(b):32} {os.path.getsize(b)/1024:8.1f} KB")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
