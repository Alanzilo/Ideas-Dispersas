from studyflow.search import Hit, _select_with_context


def test_select_pages_with_context_and_limit_legacy_name():
    hits = [Hit("A.pdf", 5, 2.0, "", ["a"])]
    selected = _select_with_context(hits, context_pages=1, max_pages_total=3)
    pages = [h.page_num for h in selected["A.pdf"]]
    assert pages == [4, 5, 6]
