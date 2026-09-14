import cv2
import numpy as np
import pytest
import config as CONFIG
from services.preprocess import preprocess_image, _deskew, _denoise, _correct_perspective, _adaptive_threshold, _upscale_to_dpi, _morphological_cleanup


class TestPreprocessSteps:
    def test_deskew_returns_image_and_angle(self):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.rectangle(img, (10, 10), (90, 90), (255, 255, 255), -1)
        
        rotated, angle = _deskew(img)
        
        assert rotated.shape == img.shape
        assert isinstance(angle, float)

    def test_denoise_returns_same_shape(self):
        img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        denoised = _denoise(img)
        
        assert denoised.shape == img.shape
        assert denoised.dtype == img.dtype

    def test_adaptive_threshold_returns_binary(self):
        img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        binary = _adaptive_threshold(img)
        
        assert binary.shape == (100, 100)
        assert binary.dtype == np.uint8
        unique = np.unique(binary)
        assert set(unique.tolist()).issubset({0, 255})

    def test_upscale_to_dpi_increases_size(self):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        
        upscaled = _upscale_to_dpi(img, target_dpi=300)
        
        assert upscaled.shape[0] > img.shape[0]
        assert upscaled.shape[1] > img.shape[1]

    def test_upscale_to_dpi_no_change_when_scale_le_1(self):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        
        upscaled = _upscale_to_dpi(img, target_dpi=72)
        
        assert upscaled.shape == img.shape

    def test_morphological_cleanup_returns_same_shape(self):
        img = np.zeros((100, 100), dtype=np.uint8)
        cv2.rectangle(img, (10, 10), (90, 90), 255, -1)
        
        cleaned = _morphological_cleanup(img)
        
        assert cleaned.shape == img.shape

    def test_deskew_corrects_known_skew(self):
        img = np.full((400, 900, 3), 255, dtype=np.uint8)
        for i, line in enumerate(["HALO DUNIA", "BARIS KEDUA", "BARIS KETIGA"]):
            cv2.putText(
                img, line, (60, 120 + i * 90),
                cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 0, 0), 4, cv2.LINE_AA,
            )

        M = cv2.getRotationMatrix2D((450, 200), 10.0, 1.0)
        skewed = cv2.warpAffine(
            img, M, (900, 400), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )

        _, angle = _deskew(skewed)

        assert angle == pytest.approx(-10.0, abs=1.0)

    def test_deskew_leaves_horizontal_text_untouched(self):
        img = np.full((200, 600, 3), 255, dtype=np.uint8)
        cv2.putText(
            img, "HALO", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 0), 4, cv2.LINE_AA
        )

        rotated, angle = _deskew(img)

        assert angle == 0.0
        assert np.array_equal(rotated, img)
        
        
    def test_deskew_corrects_negative_skew(self):
        img = np.full((400, 900, 3), 255, dtype=np.uint8)
        for i, line in enumerate(["HALO DUNIA", "BARIS KEDUA", "BARIS KETIGA"]):
            cv2.putText(img, line, (60, 120 + i * 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 0, 0), 4, cv2.LINE_AA)

        M = cv2.getRotationMatrix2D((450, 200), -7.0, 1.0)
        skewed = cv2.warpAffine(img, M, (900, 400),
                                flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

        _, angle = _deskew(skewed)

        assert angle == pytest.approx(7.0, abs=1.0)
            
    def test_perspective_restores_aspect_ratio(self):
        page = np.full((600, 420, 3), 255, dtype=np.uint8)     # rasio 0.7, mirip A4
        cv2.putText(page, "SURAT", (40, 300), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0,0,0), 4)

        scene = np.zeros((800, 800, 3), dtype=np.uint8)        # latar gelap
        src = np.float32([[0,0],[420,0],[420,600],[0,600]])
        dst = np.float32([[150,60],[650,90],[620,790],[120,750]])  # miring seperti difoto
        M = cv2.getPerspectiveTransform(src, dst)
        cv2.warpPerspective(page, M, (800,800), scene,
                            borderMode=cv2.BORDER_TRANSPARENT)

        out = _correct_perspective(scene)
        rasio = out.shape[1] / out.shape[0]

        assert rasio == pytest.approx(420/600, rel=0.15)


        
class TestPreprocessImage:
    def test_returns_preprocess_result(self):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        
        result = preprocess_image(img)
        
        assert hasattr(result, 'image')
        assert hasattr(result, 'steps_applied')
        assert hasattr(result, 'deskew_angle')
        assert hasattr(result, 'input_resolution')
        assert hasattr(result, 'output_resolution')
        assert hasattr(result, 'duration_ms')


    def test_steps_applied_contains_enabled_steps(self, semua_langkah_nyala):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        
        result = preprocess_image(img)
        
        expected_steps = [
            "deskew", "denoise", "perspective_correction",
            "adaptive_threshold", "upscale_300dpi", "morphology"
        ]
        for step in expected_steps:
            assert step in result.steps_applied

    def test_input_output_resolution_recorded(self):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        
        result = preprocess_image(img)
        
        assert result.input_resolution == (100, 100)
        assert result.output_resolution[0] > 100
        assert result.output_resolution[1] > 100

    def test_duration_ms_positive(self):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        
        result = preprocess_image(img)
        
        assert result.duration_ms > 0

    def test_output_image_is_binary_after_threshold(self, semua_langkah_nyala):
        img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        result = preprocess_image(img)
        
        unique = np.unique(result.image)
        assert set(unique.tolist()).issubset({0, 255})
        
    def test_threshold_and_morphology_skipped_when_disabled(self, semua_langkah_nyala, monkeypatch):
        monkeypatch.setattr(CONFIG, "PREPROCESS_THRESHOLD", False)
        monkeypatch.setattr(CONFIG, "PREPROCESS_MORPHOLOGY", False)
        img = np.zeros((100, 100, 3), dtype=np.uint8)

        result = preprocess_image(img)

        assert "adaptive_threshold" not in result.steps_applied
        assert "morphology" not in result.steps_applied
        
    def test_threshold_and_morphology_skipped_when_disabled(self, semua_langkah_nyala, monkeypatch):
        monkeypatch.setattr(CONFIG, "PREPROCESS_THRESHOLD", False)
        monkeypatch.setattr(CONFIG, "PREPROCESS_MORPHOLOGY", False)
        img = np.zeros((100, 100, 3), dtype=np.uint8)

        result = preprocess_image(img)

        assert "adaptive_threshold" not in result.steps_applied
        assert "morphology" not in result.steps_applied

        
@pytest.fixture
def semua_langkah_nyala(monkeypatch):
    for flag in ("PREPROCESS_DESKEW", "PREPROCESS_DENOISE", "PREPROCESS_PERSPECTIVE",
                "PREPROCESS_THRESHOLD", "PREPROCESS_MORPHOLOGY"):
        monkeypatch.setattr(CONFIG, flag, True)
    monkeypatch.setattr(CONFIG, "PREPROCESS_UPSCALE_DPI", 300)