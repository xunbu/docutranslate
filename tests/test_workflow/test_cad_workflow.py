import shutil
import pytest
from pathlib import Path
from unittest.mock import patch

from docutranslate.cad.text_extractor import CadTextExtractor
from docutranslate.cad.text_applier import CadTextApplier
from docutranslate.cad.dwg_converter import DwgConverter

TESTS_DIR = Path(__file__).parent
TEST_DWG = TESTS_DIR / "test_cad_input.dwg"
TEST_DXF = TESTS_DIR / "test_cad_simple.dxf"


def _libredwg_available() -> bool:
    return shutil.which("dwg2dxf") is not None


requires_libredwg = pytest.mark.skipif(
    not _libredwg_available() or not TEST_DWG.exists(),
    reason="LibreDWG (dwg2dxf) or test DWG file not available"
)


# ======================================================================
# CadTextExtractor
# ======================================================================

def test_extractor_returns_error_without_ezdxf():
    """Extractor should return error if ezdxf is not installed."""
    with patch.dict("sys.modules", {"ezdxf": None}):
        extractor = CadTextExtractor()
        result = extractor.extract("nonexistent.dxf")
        assert result.success is False
        assert "ezdxf" in result.message.lower() or "install" in result.message.lower()


def test_extractor_returns_error_for_missing_file():
    extractor = CadTextExtractor()
    result = extractor.extract("nonexistent.dxf")
    assert result.success is False
    assert "not found" in result.message.lower()


# ======================================================================
# CadTextApplier
# ======================================================================

def test_applier_returns_error_without_ezdxf():
    with patch.dict("sys.modules", {"ezdxf": None}):
        applier = CadTextApplier()
        result = applier.apply("a.dxf", "b.dxf", {"hello": "world"})
        assert result.success is False
        assert "ezdxf" in result.message.lower() or "install" in result.message.lower()


def test_applier_returns_error_for_missing_file():
    applier = CadTextApplier()
    result = applier.apply("nonexistent.dxf", "output.dxf", {"hello": "world"})
    assert result.success is False
    assert "not found" in result.message.lower()


# ======================================================================
# DwgConverter
# ======================================================================

def test_converter_dxf_passthrough(tmp_path):
    """If input is already DXF, just copy it."""
    dxf_file = tmp_path / "test.dxf"
    dxf_file.write_text("DXF content", encoding="utf-8")

    converter = DwgConverter(backend="dxf_only")
    result = converter.dwg_to_dxf(str(dxf_file), str(tmp_path / "output"))

    assert result.success is True
    assert result.output_path is not None
    assert Path(result.output_path).exists()


def test_converter_no_backend(tmp_path):
    dwg_file = tmp_path / "test.dwg"
    dwg_file.write_text("fake dwg", encoding="utf-8")
    converter = DwgConverter(backend="dxf_only")
    result = converter.dwg_to_dxf(str(dwg_file), str(tmp_path / "output"))
    assert result.success is False
    assert "dxf_only" in result.message.lower() or "already dxf" in result.message.lower()


def test_converter_detect_available():
    converter = DwgConverter()
    available = converter.detect_available()
    assert isinstance(available, dict)
    assert "libredwg" in available


def test_converter_missing_file():
    converter = DwgConverter()
    result = converter.dwg_to_dxf("nonexistent.dwg", "output")
    assert result.success is False
    assert "not found" in result.message.lower()


# ======================================================================
# Integration Tests (require LibreDWG + test DWG file)
# ======================================================================

@requires_libredwg
def test_dwg_to_dxf_conversion(tmp_path):
    """Convert real DWG file to DXF using LibreDWG."""
    converter = DwgConverter(backend="libredwg")
    output_dir = tmp_path / "output"
    result = converter.dwg_to_dxf(str(TEST_DWG), str(output_dir))

    assert result.success is True, f"Conversion failed: {result.message}"
    assert result.output_path is not None
    assert Path(result.output_path).exists()
    assert result.output_path.endswith(".dxf")
    assert result.backend_used == "libredwg"


def test_extract_text_from_dxf():
    """Extract text entities from a DXF file."""
    if not TEST_DXF.exists():
        pytest.skip("Test DXF file not found")

    extractor = CadTextExtractor()
    result = extractor.extract(str(TEST_DXF))

    assert result.success is True, f"Extraction failed: {result.message}"
    assert len(result.entities) >= 2, f"Expected at least 2 entities, got {len(result.entities)}"

    texts = [e.text for e in result.entities]
    assert "Hello World" in texts
    assert "Test Label" in texts

    for entity in result.entities:
        assert entity.text, "Entity text should not be empty"
        assert entity.entity_type in ("TEXT", "MTEXT", "ATTDEF", "ATTRIB")


def test_apply_translations_to_dxf(tmp_path):
    """Apply translations to a DXF file and verify output."""
    if not TEST_DXF.exists():
        pytest.skip("Test DXF file not found")

    extractor = CadTextExtractor()
    extract_result = extractor.extract(str(TEST_DXF))
    assert extract_result.success is True

    translation_map = {}
    for entity in extract_result.entities:
        if entity.entity_type == "TEXT":
            translation_map[entity.text] = f"翻译_{entity.text}"

    applier = CadTextApplier()
    output_dxf = tmp_path / "translated.dxf"
    apply_result = applier.apply(
        str(TEST_DXF),
        str(output_dxf),
        translation_map,
    )

    assert apply_result.success is True, f"Apply failed: {apply_result.message}"
    assert apply_result.translated_count > 0
    assert output_dxf.exists()

    verify = CadTextExtractor()
    verify_result = verify.extract(str(output_dxf))
    assert verify_result.success is True
    translated_texts = [e.text for e in verify_result.entities]
    assert any(t.startswith("翻译_") for t in translated_texts), "No translated text found"


def test_full_cad_pipeline(tmp_path):
    """Full pipeline: DXF → Extract → Translate → Apply."""
    if not TEST_DXF.exists():
        pytest.skip("Test DXF file not found")

    extractor = CadTextExtractor()
    extract_result = extractor.extract(str(TEST_DXF))
    assert extract_result.success is True
    assert len(extract_result.entities) > 0

    translation_map = {}
    for entity in extract_result.entities:
        translation_map[entity.text] = f"[CN] {entity.text}"

    applier = CadTextApplier()
    final_dxf = tmp_path / "final.dxf"
    apply_result = applier.apply(
        str(TEST_DXF),
        str(final_dxf),
        translation_map,
        mode="replace",
        font_name="SimSun",
    )
    assert apply_result.success is True
    assert final_dxf.exists()

    verify = CadTextExtractor()
    verify_result = verify.extract(str(final_dxf))
    assert verify_result.success is True
    has_translated = any(e.text.startswith("[CN]") for e in verify_result.entities)
    assert has_translated, "No translated text found in output DXF"
