# Dokumen Pengujian — ocr-engine

**Peran pemilik dokumen**: @quality-assurance
**Versi service**: 0.1.0
**Tanggal eksekusi terakhir**: 14 September 2026
**Hasil**: 39 lolos, 0 gagal, 21,88 detik

## 1. Ruang Lingkup

Yang diuji adalah `ocr-engine/`: satu service yang menerima berkas dan mengembalikan teks beserta
koordinat dan confidence per kata. Pemetaan teks menjadi field dokumen bukan tanggung jawab
service ini dan tidak diuji di sini.

**Yang diuji:**

| Area | Bentuk pengujian |
|---|---|
| Pemilihan jalur pemrosesan | Text layer PDF, raster PDF, gambar |
| Validasi berkas | Tipe menurut magic bytes, ukuran, jumlah halaman |
| Preprocessing | Deskew, denoise, koreksi perspektif, upscale, binarisasi, morfologi |
| Bentuk respons | Struktur, normalisasi `bbox`, nilai `confidence`, `engine` per jalur |
| Isi bacaan | Kata kunci yang harus muncul pada dokumen fixture |
| Penanganan kesalahan | Berkas rusak, tipe tidak didukung, melebihi batas |

**Yang tidak diuji:**

| Area | Alasan |
|---|---|
| Akurasi terhadap dokumen asli | Belum ada golden dataset. Seluruh fixture adalah dokumen buatan |
| Observability | Logging terstruktur, tracing, dan metrik belum diimplementasikan |
| Beban dan konkurensi | Belum ada target throughput yang ditetapkan |
| Keamanan ingress | Service ini tidak memiliki ingress; validasi paranoid berada di layanan pintu masuk |

## 2. Strategi

Tiga hal yang membentuk cara pengujian ini disusun:

1. **Berjenjang.** Fungsi preprocessing diuji satuan dengan gambar sintetis yang sifatnya
   diketahui (kotak putih pada latar hitam, teks yang sengaja dimiringkan 10°). Jalur ujung ke
   ujung diuji dengan berkas fixture menyerupai dokumen nyata. Fungsi satuan menjelaskan
   **kenapa** gagal, uji ujung ke ujung menjelaskan **bahwa** gagal.
2. **Dapat dijalankan tanpa Tesseract.** Uji yang membutuhkan biner Tesseract diberi marker `ocr`
   dan dilewati otomatis bila binernya tidak ada (`tests/conftest.py`). Dengan begitu kontributor
   tanpa Tesseract tetap dapat menjalankan suite dan CI Linux tetap berguna.
3. **Fixture ter-commit, bukan dibuat ulang saat uji.** Berkas fixture dihasilkan oleh
   `tests/fixtures/generate_fixtures.py` yang membutuhkan font Times New Roman dari Windows.
   Berkas hasilnya di-commit sebagai baseline bersama; skripnya ada untuk menerangkan asal-usul
   dan membuat varian baru.

## 3. Lingkungan Pengujian

| Komponen | Versi |
|---|---|
| Python | 3.9.13 |
| Tesseract | 5.4.0.20240606 (leptonica 1.84.1) |
| OpenCV | 4.10.0 (opencv-python-headless) |
| PyMuPDF | 1.26.5 |
| FastAPI | 0.128.8 |
| Pydantic | 2.13.5 |
| pytest | 8.4.2 |
| Sistem operasi | Windows 11 |

Konfigurasi preprocessing saat eksekusi: deskew **nyala**, denoise **nyala**, koreksi perspektif
**nyala**, upscale 300 DPI **nyala**, binarisasi adaptif **mati**, morfologi **mati**.

## 4. Cara Menjalankan

```bash
pip install -r requirements-dev.txt

pytest                    # seluruh uji
pytest -v                 # dengan nama tiap kasus
pytest -m "not slow"      # lewati OCR halaman penuh (lebih cepat)
pytest -m ocr             # hanya yang membutuhkan Tesseract
pytest tests/test_preprocess.py::TestPreprocessSteps::test_deskew_corrects_known_skew
```

Marker yang dipakai: `ocr` (butuh biner Tesseract) dan `slow` (OCR satu halaman penuh, hitungan
detik).

## 5. Daftar Kasus Uji

### 5.1 `test_health.py` — 1 kasus

| Kasus | Yang dikunci |
|---|---|
| `test_health_ok` | `/health` mengembalikan 200 dan **tepat** empat kunci. Uji ini menangkap kebocoran informasi bila kelak ada yang menambahkan detail internal ke respons health |

### 5.2 `test_mime_detection.py` — 4 kasus

| Kasus | Yang dikunci |
|---|---|
| `test_accepts_allowed_types` | JPG, PNG, dan PDF diterima |
| `test_rejects_unknown_signature` | Berkas dengan magic bytes asing ditolak. **Tipe ditentukan dari isi berkas, bukan dari ekstensi atau `Content-Type` kiriman klien** |
| `test_rejects_oversized_image` | Gambar > 10 MB ditolak `FILE_TOO_LARGE` |
| `test_rejects_oversized_pdf` | PDF > 25 MB ditolak `FILE_TOO_LARGE` |

### 5.3 `test_pdf_text.py` — 4 kasus

| Kasus | Yang dikunci |
|---|---|
| `test_pdf_text_layer_creator` | PDF ber-text-layer memberi `ocr_source` = `text_layer`, `engine` = `null`, dan jumlah kata yang tepat. `engine` null membuktikan tidak ada OCR yang dijalankan |
| `test_exact_text_match` | Nomor surat dan tempat tujuan terbaca **persis**. Inilah keunggulan jalur ini: tidak ada karakter yang ditebak |
| `test_bounding_box_always_normalized` | Seluruh `bbox` berada di rentang 0–1 dan `confidence` = 1,0 |
| `test_deny_pdf_without_text` | PDF kosong ditolak sebagai text layer tidak memadai, sehingga dialihkan ke jalur OCR alih-alih mengembalikan halaman kosong |

### 5.4 `test_pdf_raster.py` — 9 kasus

| Kasus | Yang dikunci |
|---|---|
| `test_converts_rgb_to_bgr` | Konversi pixmap PyMuPDF (RGB) ke urutan kanal OpenCV (BGR). Tertukarnya kanal tidak membuat program gagal, hanya menurunkan akurasi diam-diam |
| `test_rejects_invalid_pdf` | Berkas teks biasa ditolak `INVALID_PDF` |
| `test_rejects_over_page_limit` | Melebihi `PDF_MAX_PAGES` ditolak, **tidak dipotong diam-diam** |
| `test_returns_ocr_response` | `ocr_source` = `ocr`, `engine` terisi, `duration_ms` > 0 |
| `test_reads_document_content` | Judul, tempat tujuan, dua nama pegawai, dan satu NIP 18 digit terbaca |
| `test_reads_document_number` | Nomor surat `090/ST/IX/2026` terbaca lengkap dengan garis miringnya |
| `test_rasters_at_configured_dpi` | A4 pada 300 DPI menghasilkan sekitar 2480 x 3508 piksel |
| `test_bbox_is_normalized` | Seluruh koordinat berada di rentang 0–1 |
| `test_reads_every_page` | PDF dua halaman menghasilkan dua halaman berurutan, dan isi halaman kedua (lampiran beserta nominalnya) ikut terbaca |

### 5.5 `test_image_ocr.py` — 5 kasus

| Kasus | Yang dikunci |
|---|---|
| `test_decodes_png` | PNG terdekode menjadi larik tiga kanal |
| `test_rejects_undecodable_bytes` | Berkas ber-magic-bytes PNG tetapi isinya rusak ditolak `UNSUPPORTED_MEDIA_TYPE`, bukan melempar galat mentah |
| `test_returns_ocr_response` | Bentuk respons dan identitas mesin |
| `test_recognizes_rendered_text` | Teks yang digambar ke citra terbaca kembali |
| `test_bbox_is_normalized` | Seluruh koordinat berada di rentang 0–1 |

### 5.6 `test_preprocess.py` — 16 kasus

**Fungsi satuan:**

| Kasus | Yang dikunci |
|---|---|
| `test_deskew_returns_image_and_angle` | Bentuk keluaran deskew |
| `test_deskew_corrects_known_skew` | Kemiringan +10° terdeteksi dengan toleransi 1° |
| `test_deskew_corrects_negative_skew` | Kemiringan −7° terdeteksi. Uji ini menjaga penanganan tanda sudut, sumber bug klasik pada `minAreaRect` |
| `test_deskew_leaves_horizontal_text_untouched` | Gambar lurus dikembalikan **identik**, tanpa rotasi 0° yang tetap mengaburkan piksel karena interpolasi |
| `test_denoise_returns_same_shape` | Denoise tidak mengubah dimensi atau tipe data |
| `test_adaptive_threshold_returns_binary` | Keluaran hanya bernilai 0 dan 255 |
| `test_upscale_to_dpi_increases_size` | Upscale ke 300 DPI memperbesar gambar |
| `test_upscale_to_dpi_no_change_when_scale_le_1` | Target lebih kecil dari sumber tidak memperkecil gambar |
| `test_morphological_cleanup_returns_same_shape` | Morfologi tidak mengubah dimensi |
| `test_perspective_restores_aspect_ratio` | Halaman yang difoto menyudut dikembalikan ke rasio aslinya dengan toleransi 15% |

**Orkestrasi:**

| Kasus | Yang dikunci |
|---|---|
| `test_returns_preprocess_result` | Seluruh atribut hasil tersedia untuk pencatatan diagnostik |
| `test_steps_applied_contains_enabled_steps` | Langkah yang menyala tercatat di `steps_applied` |
| `test_input_output_resolution_recorded` | Resolusi sebelum dan sesudah tercatat |
| `test_duration_ms_positive` | Durasi terukur |
| `test_output_image_is_binary_after_threshold` | Dengan binarisasi menyala, keluaran benar-benar biner |
| `test_threshold_and_morphology_skipped_when_disabled` | Saklar konfigurasi benar-benar mematikan langkahnya |

## 6. Pengujian Manual Terhadap Dokumen Kusut

Di luar suite otomatis, dua fixture foto dokumen kusut dikirim ke endpoint `POST /ocr` untuk
melihat perilaku pada kondisi buruk. Hasil pada foto kusut ringan dijadikan acuan, lalu
dibandingkan dengan foto kusut berat.

| Bagian | Kusut ringan | Kusut berat | Dampak |
|---|---|---|---|
| Nomor telepon kop | `3449230,` | `3449230:` | Ringan |
| Garis kop | Tidak terbaca | Terbaca sebagai deretan simbol | Kata sampah |
| Golongan pegawai 1 | `III-b` | `1II-D` | **Nilai rusak** |
| Golongan pegawai 2 | `III-c` | `III-€` | **Nilai rusak** |
| Label tanggal | `Tanggal`, `Kembali` | `Tanggai`, `Kembati` | Jangkar parser hilang |
| Lama perjalanan | `: 4 (empat) hari` | `"4 Cempat) hari` | Pemisah hilang |
| Pembebanan anggaran | `DIPA Ditjen …` | Kata `DIPA` **hilang** | **Nilai salah tanpa penanda** |

Yang tetap benar pada kedua foto: seluruh NIP, seluruh tanggal, seluruh nama, dan nomor surat.

### Tiga temuan yang memengaruhi rancangan sistem

1. **`confidence` tidak dapat dipakai sebagai penanda kesalahan.** Kata `3449230:` yang salah
   bernilai 0,90, sedangkan `Pangkat/Golongan` yang benar bernilai 0,48 dan `Santoso` yang benar
   bernilai 0,53. Nilai ini mengukur keyakinan pengenalan bentuk huruf, bukan kebenaran isinya.
   Penanda "perlu diperiksa" di aplikasi tidak boleh hanya bersandar pada angka ini.
2. **Kata yang hilang adalah kegagalan paling berbahaya.** `Ditjen Perbendaharaan TA 2026` tampak
   wajar sehingga tidak ada mekanisme hilir yang dapat mengetahui bahwa `DIPA` pernah ada.
   Perbaikannya harus di preprocessing, bukan di pemrosesan teks.
3. **Binarisasi adaptif merugikan pada konfigurasi saat ini.** Dengan `blockSize` tetap 11 pada
   gambar yang sudah diperbesar sekitar empat kali, bagian dalam goresan huruf tebal menjadi
   putih. Karena itu `PREPROCESS_THRESHOLD` dimatikan secara bawaan dan Tesseract dibiarkan
   membinarisasi sendiri.

## 7. Batasan Pengujian Ini

**Fixture bukan pengukur akurasi.** Seluruh berkas uji dihasilkan program dengan satu tata letak,
satu font, tanpa stempel, tanpa kop berlogo, tanpa kertas menguning, dan tanpa tulisan tangan.
Fixture menutup jalur kode dan mengunci regresi — lolosnya seluruh uji **tidak** berarti akurasi
sistem memadai.

Angka akurasi yang sahih hanya dapat diperoleh dari dokumen asli. Pengumpulan dokumen contoh
nyata masih menjadi pertanyaan terbuka pada dokumen produk, dan menjadi prasyarat sebelum akurasi
dapat diklaim.

Data pada seluruh fixture bersifat fiktif: nama, NIP, dan nomor surat dikarang untuk keperluan
uji.

## 8. Rekomendasi Lanjutan

| # | Rekomendasi | Alasan |
|---|---|---|
| 1 | Kumpulkan golden dataset dokumen asli beserta teks acuannya | Tanpa itu, tidak ada angka akurasi yang dapat dipertanggungjawabkan |
| 2 | Ukur akurasi per field, bukan hanya tingkat kesalahan karakter | Satu karakter salah pada NIP jauh lebih merugikan daripada satu karakter salah pada uraian tugas |
| 3 | Uji varian preprocessing secara berdampingan: resolusi sumber sebenarnya, tanpa binarisasi, normalisasi pencahayaan | Tiga tuas ini paling berpengaruh pada foto dokumen kusut dan berbayang |
| 4 | Tambahkan uji untuk observability setelah diimplementasikan | Termasuk memastikan teks hasil OCR tidak pernah masuk log |
| 5 | Tambahkan uji batas jumlah halaman pada jalur text layer | Saat ini batas hanya diperiksa pada jalur raster |
| 6 | Uji beban setelah target throughput ditetapkan | OCR bersifat CPU-bound; perilaku saat banyak permintaan bersamaan belum diketahui |
