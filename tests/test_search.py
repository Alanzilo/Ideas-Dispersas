from studyflow.search import Hit, _select_with_context


def test_select_pages_with_context_and_limit():
    hits = [
        Hit("A.pdf", 10, 5.0, "a", ["shock"]),
        Hit("A.pdf", 30, 2.0, "b", ["sepsis"]),
    ]
    selected = _select_with_context(hits, context_pages=1, max_pages_total=5)
    pages = [h.page_num for h in selected["A.pdf"]]
    assert 9 in pages and 10 in pages and 11 in pages
    assert len(pages) <= 5
