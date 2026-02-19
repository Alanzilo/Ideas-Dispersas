from app.main import _build_manifest
from app.searcher import PageHit


def test_manifest_structure():
    search_result = {
        "keywords": ["shock", "septico"],
        "selected_pages": {
            "Fuentes/A.pdf": [
                PageHit("Fuentes/A.pdf", 1, 3.0, ["shock"]),
                PageHit("Fuentes/A.pdf", 2, 0.5, ["context"]),
            ]
        },
    }
    manifest = _build_manifest("2026-02-19", "Shock séptico", {"x": 1}, search_result, [])
    assert manifest["date"] == "2026-02-19"
    assert manifest["topic"] == "Shock séptico"
    assert "pages_included_by_source" in manifest
    assert "included_page_details" in manifest
