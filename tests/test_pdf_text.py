import pytest

from error_handlers.errors import InvalidPdfError, TextLayerUnusableError
from services.pdf_text import extract_text



def test_pdf_text_layer_creator(read_fixture):
    result = extract_text(read_fixture("sample_text.pdf"))
    
    assert result.ocr_source == "text_layer"
    assert result.page_count == 1
    assert result.engine is None
    assert len(result.pages[0].words) == 24
    
def test_exact_text_match(read_fixture):
    result = extract_text(read_fixture("sample_text.pdf"))
    
    assert "090/SPD/IX/2026" in result.pages[0].text
    assert "SURABAYA" in result.pages[0].text
    
def test_bounding_box_always_normalized(read_fixture):
    result = extract_text(read_fixture("sample_text.pdf"))
    
    for page in result.pages:
        for word in page.words:
            assert len(word.bbox) == 4
            assert all(0.0 <= res <= 1.0 for res in word.bbox)
            assert word.confidence == 1.0
            
def test_deny_pdf_without_text(read_fixture):
    with pytest.raises(TextLayerUnusableError):
        extract_text(read_fixture("blank.pdf"))