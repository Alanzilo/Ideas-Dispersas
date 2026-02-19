from studyflow.cli import _manifest
from studyflow.search import Hit


def test_manifest_structure():
    result = {
        "applied_synonyms": ["shock septico"],
        "selected_pages": {
            "Fuentes/A.pdf": [
                Hit("Fuentes/A.pdf", 1, 1.4, "text", ["shock"]),
                Hit("Fuentes/A.pdf", 2, 0.3, "ctx", ["context"]),
            ]
        },
    }
    manifest = _manifest("2026-02-19", "Shock séptico", {"x": 1}, result, [])
    assert manifest["date"] == "2026-02-19"
    assert manifest["topic"] == "Shock séptico"
    assert "pages_included_by_source" in manifest
    assert "included_page_details" in manifest
