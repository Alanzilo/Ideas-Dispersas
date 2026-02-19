from app.utils import sanitize_filename


def test_sanitize_filename_basic():
    assert sanitize_filename("Shock séptico: diagnóstico/manejo") == "Shock_séptico_diagnóstico_manejo"
