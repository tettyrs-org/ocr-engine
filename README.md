# ocr-engine

Service OCR untuk dokumen perjalanan dinas: menerima gambar atau PDF, mengembalikan teks
beserta koordinat dan tingkat keyakinan per kata.

Service ini sengaja dibuat **tidak tahu konteks bisnis**. Ia tidak mengenal apa itu Surat Tugas,
NIP, atau tanggal berangkat. Tugasnya satu: mengubah piksel menjadi teks yang dapat dipetakan
oleh layanan lain. Dengan batas sesempit itu, mesin OCR di dalamnya dapat diganti tanpa
menyentuh pemanggilnya.

```
berkas (JPG/PNG/PDF)
        |
        v
  PDF punya text layer? --- ya ---> baca langsung (PyMuPDF), akurasi eksak, ~50 ms
        |
       tidak
        v
  preprocessing (OpenCV: deskew, denoise, koreksi perspektif, upscale)
        |
        v
  Tesseract  --->  teks + bbox + confidence per kata
```

## Persyaratan

| Kebutuhan | Versi yang diuji |
|---|---|
| Python | 3.9.13 |
| Tesseract OCR | 5.4.0 |
| Data bahasa Tesseract | `ind` (Indonesia) |

## 1. Pasang Tesseract

Tesseract adalah program terpisah, bukan pustaka Python. Ia harus terpasang lebih dulu.

**Windows** — unduh installer dari [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki).
Saat memasang, buka **Additional language data** lalu centang **Indonesian**. Tanpa itu,
service gagal dengan pesan bahwa data bahasa `ind` tidak ditemukan.

**Linux (Debian/Ubuntu)**

```bash
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-ind
```

**macOS**

```bash
brew install tesseract tesseract-lang
```

Pastikan hasilnya terbaca:

```bash
tesseract --version
tesseract --list-langs    # harus memuat "ind"
```

## 2. Pasang service

```bash
git clone https://github.com/tettyrs/ocr-engine.git
cd ocr-engine

python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## 3. Konfigurasi

```bash
cp .env.example .env      # Windows: copy .env.example .env
```

`config.py` **tidak memiliki nilai default**. Setiap kunci di `.env.example` wajib ada, kecuali
yang ditandai boleh kosong. Kunci yang hilang membuat service gagal saat diimpor dengan pesan
yang tidak menyebut nama variabelnya — lihat baris pada traceback untuk menemukannya.

Dua kunci yang biasanya perlu disesuaikan:

```ini
TESSERACT_DATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

Keduanya boleh dikosongkan bila Tesseract sudah ada di `PATH` dan memakai lokasi bawaan.

> **Jebakan path Windows.** Jangan mengapit path dengan kutip ganda.
> `python-dotenv` memproses escape sequence di dalam kutip ganda, sehingga
> `"C:\Tesseract-OCR\tessdata"` membuat `\t` menjadi TAB dan path-nya rusak tanpa pesan error.
> Tulis tanpa kutip, atau pakai kutip tunggal.

Konfigurasi selengkapnya:

| Kunci | Arti |
|---|---|
| `OCR_HOST`, `OCR_PORT` | Alamat service. Bawaan `127.0.0.1:8082` |
| `OCR_TEXT_LAYER_MIN_CHARS` | Ambang rata-rata karakter per halaman agar text layer PDF dianggap layak. Di bawahnya, dokumen dialihkan ke jalur OCR |
| `PREPROCESS_DESKEW` | Meluruskan halaman yang miring |
| `PREPROCESS_DENOISE` | Meredam bintik pada foto |
| `PREPROCESS_PERSPECTIVE` | Meluruskan foto yang diambil menyudut |
| `PREPROCESS_THRESHOLD` | Binarisasi adaptif. **Bawaan mati**: Tesseract membinarisasi sendiri, dan pada fixture uji langkah ini justru membuat huruf tebal berongga |
| `PREPROCESS_MORPHOLOGY` | Perapian morfologis. Bawaan mati, hanya bermakna bila binarisasi menyala |
| `PREPROCESS_UPSCALE_DPI` | Target resolusi sebelum OCR |
| `PDF_RASTER_DPI` | Resolusi render halaman PDF tanpa text layer |
| `PDF_MAX_PAGES` | Batas jumlah halaman PDF |
| `OCR_ENGINE` | Nama mesin yang terdaftar di `OcrEngineFactory`. Saat ini `tesseract` |
| `TESSERACT_LANG` | Bahasa Tesseract, `ind` |

Nilai boolean hanya mengenali `true` (besar-kecil bebas). Salah ketik seperti `ture` diam-diam
dianggap `false`.

## 4. Jalankan

```bash
python main.py
```

atau

```bash
uvicorn main:app --host 127.0.0.1 --port 8082 --reload
```

Dokumentasi interaktif tersedia di <http://127.0.0.1:8082/docs>.

## Endpoint

### `GET /health`

```json
{ "status": "ok", "service": "ocr-engine", "version": "0.1.0", "environment": "local" }
```

### `POST /ocr`

`multipart/form-data` dengan satu bagian `file` berisi JPG, PNG, atau PDF.

```bash
curl -X POST http://127.0.0.1:8082/ocr \
  -H 'accept: application/json' \
  -F 'file=@surat_tugas.jpg;type=image/jpeg'
```

```json
{
  "ocr_source": "ocr",
  "engine": { "name": "tesseract", "version": "5.4.0.20240606" },
  "page_count": 1,
  "duration_ms": 3340,
  "pages": [
    {
      "page": 1,
      "width": 5166,
      "height": 7308,
      "deskew_angle": 0.0,
      "text": "KEMENTERIAN KEUANGAN REPUBLIK INDONESIA ...",
      "words": [
        { "text": "KEMENTERIAN", "bbox": [0.193, 0.043, 0.379, 0.055], "confidence": 0.92 }
      ]
    }
  ]
}
```

| Field | Arti |
|---|---|
| `ocr_source` | `text_layer` bila teks diambil langsung dari PDF, `ocr` bila lewat pengenalan gambar |
| `engine` | `null` pada jalur `text_layer` — tidak ada mesin OCR yang dijalankan |
| `deskew_angle` | Derajat rotasi yang diterapkan preprocessing, berguna saat menyelidiki hasil buruk |
| `bbox` | `[x0, y0, x1, y1]` dinormalisasi 0–1 terhadap ukuran halaman, bukan piksel |
| `confidence` | 0–1 per kata. Selalu `1.0` pada jalur `text_layer` |

**Jangan memakai `confidence` sebagai penanda kata yang salah.** Pada pengujian, kata yang salah
baca justru bernilai 0,90 sementara kata yang benar bernilai 0,48. Nilai ini mengukur keyakinan
pengenalan bentuk huruf, bukan kebenaran isinya. Lihat [TESTING.md](TESTING.md) bagian 6.

### Kesalahan

Bentuk respons: `{ "error": { "code": "...", "message": "..." } }`

| HTTP | `code` | Kapan |
|---|---|---|
| 400 | `UNSUPPORTED_MEDIA_TYPE` | Bukan JPG/PNG/PDF menurut magic bytes, bukan menurut ekstensi |
| 400 | `INVALID_PDF` | Berkas mengaku PDF tetapi tidak dapat dibuka |
| 400 | `PAGE_LIMIT_EXCEEDED` | PDF melebihi `PDF_MAX_PAGES` |
| 413 | `FILE_TOO_LARGE` | Gambar > 10 MB atau PDF > 25 MB |
| 503 | `OCR_ENGINE_UNAVAILABLE` | Tesseract tidak terpasang atau gagal dijalankan |
| 500 | `INTERNAL_ERROR` | Kegagalan tak terduga |

## Pengujian

```bash
pip install -r requirements-dev.txt
pytest
```

Uji yang membutuhkan Tesseract akan **dilewati otomatis** bila binernya tidak ada, sehingga suite
tetap dapat dijalankan di mesin tanpa Tesseract.

```bash
pytest -m "not slow"      # lewati OCR halaman penuh
pytest -m ocr             # hanya yang membutuhkan Tesseract
```

Rincian strategi, daftar kasus uji, dan hasil eksekusi terakhir ada di [TESTING.md](TESTING.md)
beserta versi PDF-nya di [docs/laporan-pengujian-ocr-engine.pdf](docs/laporan-pengujian-ocr-engine.pdf).

## Struktur

```
main.py                 entry point FastAPI, /health
config.py               pembacaan .env, tanpa nilai default
routes/ocr.py           POST /ocr: deteksi tipe berkas, validasi, pemilihan jalur
services/pdf_text.py    jalur text layer PDF (PyMuPDF)
services/pdf_raster.py  render PDF menjadi gambar lalu OCR
services/image_ocr.py   jalur gambar: preprocessing + pemanggilan mesin OCR
services/preprocess.py  OpenCV: deskew, denoise, perspektif, upscale, binarisasi
engines/base.py         antarmuka mesin OCR + factory
engines/tesseract.py    implementasi Tesseract
schemas/ocr.py          bentuk respons (Pydantic)
error_handlers/         kesalahan domain dan handler-nya
tests/                  pytest, termasuk fixture dokumen buatan
```

Mesin OCR baru cukup mewarisi `OcrEngine` lalu mendaftar ke `OcrEngineFactory`; tidak ada bagian
lain yang perlu berubah.

## Batasan yang diketahui

Dicatat terbuka agar tidak dikira sudah tertangani:

- **Observability belum terpasang.** Pustakanya sudah ada di `requirements.txt`, tetapi logging
  terstruktur, tracing OTLP, dan endpoint metrik belum diimplementasikan.
- **Field `text` belum seragam antar jalur.** Jalur text layer mempertahankan baris, jalur OCR
  menggabungkan kata dengan spasi. Pemanggil sebaiknya menyusun baris sendiri dari `bbox`.
- **`width` dan `height` pada jalur gambar adalah ukuran setelah preprocessing**, bukan ukuran
  berkas asli. Bila koreksi perspektif memotong gambar, `bbox` tidak lagi sejajar dengan foto
  aslinya.
- **Resolusi sumber gambar diasumsikan 72 DPI**, sehingga foto beresolusi tinggi ikut diperbesar
  lebih jauh dari yang diperlukan.
- **Batas jumlah halaman hanya diperiksa pada jalur raster**, belum pada jalur text layer.
- **Akurasi belum diukur terhadap dokumen asli.** Seluruh fixture adalah dokumen buatan dengan
  satu tata letak dan satu font.

## Lisensi

Belum ditentukan.
