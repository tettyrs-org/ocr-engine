import numpy as np
import pymupdf
import pytest

import config as CONFIG
from error_handlers.errors import InvalidPdfError, PageLimitExceededError
from services.pdf_raster import _pixmap_to_bgr, extract_pdf_raster


def _pdf_halaman_merah() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=100, height=100)
    page.draw_rect(pymupdf.Rect(0, 0, 100, 100), color=(1, 0, 0), fill=(1, 0, 0))
    data = doc.tobytes()
    doc.close()

    return data


@pytest.fixture(scope="module")
def hasil_satu_halaman(read_fixture):
    return extract_pdf_raster(read_fixture("surat_tugas_scan.pdf"))


@pytest.fixture(scope="module")
def hasil_dua_halaman(read_fixture):
    return extract_pdf_raster(read_fixture("surat_tugas_2halaman.pdf"))


class TestPixmapToBgr:
    def test_converts_rgb_to_bgr(self):
        with pymupdf.open(stream=_pdf_halaman_merah(), filetype="pdf") as doc:
            pix = doc[0].get_pixmap(dpi=72, colorspace=pymupdf.csRGB, alpha=False)
            tinggi, lebar = pix.height, pix.width
            bgr = _pixmap_to_bgr(pix)

        assert bgr.shape == (tinggi, lebar, 3)
        assert bgr.dtype == np.uint8

        biru, hijau, merah = bgr[tinggi // 2, lebar // 2]
        assert merah > 200
        assert hijau < 60
        assert biru < 60


class TestValidasi:
    def test_rejects_invalid_pdf(self, read_fixture):
        with pytest.raises(InvalidPdfError):
            extract_pdf_raster(read_fixture("not_a_pdf.txt"))

    def test_rejects_over_page_limit(self, monkeypatch, read_fixture):
        monkeypatch.setattr(CONFIG, "PDF_MAX_PAGES", 1)

        with pytest.raises(PageLimitExceededError):
            extract_pdf_raster(read_fixture("surat_tugas_2halaman.pdf"))


@pytest.mark.ocr
@pytest.mark.slow
class TestExtractPdfRaster:
    def test_returns_ocr_response(self, hasil_satu_halaman):
        assert hasil_satu_halaman.ocr_source == "ocr"
        assert hasil_satu_halaman.page_count == 1
        assert hasil_satu_halaman.duration_ms > 0
        assert hasil_satu_halaman.engine is not None
        assert hasil_satu_halaman.engine.name == "tesseract"

    def test_reads_document_content(self, hasil_satu_halaman):
        teks = hasil_satu_halaman.pages[0].text.upper()

        assert "SURAT TUGAS" in teks
        assert "SURABAYA" in teks
        assert "BUDI SANTOSO" in teks
        assert "SITI RAHAYU" in teks
        assert "198503122010011004" in teks
        

    def test_reads_document_number(self, hasil_satu_halaman):
        assert "090/ST/IX/2026" in hasil_satu_halaman.pages[0].text
    

    def test_rasters_at_configured_dpi(self, hasil_satu_halaman):
        page = hasil_satu_halaman.pages[0]

        # A4 pada 300 DPI ~ 2480 x 3508 piksel
        assert page.width == pytest.approx(2480, abs=20)
        assert page.height == pytest.approx(3508, abs=20)

    def test_bbox_is_normalized(self, hasil_satu_halaman):
        words = hasil_satu_halaman.pages[0].words

        assert words
        for word in words:
            for coord in word.bbox:
                assert 0.0 <= coord <= 1.0

    def test_reads_every_page(self, hasil_dua_halaman):
        assert hasil_dua_halaman.page_count == 2
        assert [p.page for p in hasil_dua_halaman.pages] == [1, 2]
        assert "SURAT TUGAS" in hasil_dua_halaman.pages[0].text.upper()

        lampiran = hasil_dua_halaman.pages[1].text.upper()
        assert "LAMPIRAN" in lampiran
        assert "6.370.000" in lampiran
