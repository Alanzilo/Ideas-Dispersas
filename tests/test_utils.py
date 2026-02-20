from studyflow.utils import normalize_text, sanitize_filename


def test_sanitize_filename_basic():
    assert sanitize_filename("Shock séptico: diagnóstico/manejo") == "Shock_séptico_diagnóstico_manejo"


def test_normalize_text_accents():
    assert normalize_text("Séptico, diagnóstico") == "septico  diagnostico"
