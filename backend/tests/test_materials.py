from app.services.material_service import build_chunks


def test_build_chunks_maps_pages_one_indexed():
    chunks = build_chunks("mat-1", ["page one text", "page two text"])

    assert len(chunks) == 2
    assert chunks[0].material_id == "mat-1"
    assert chunks[0].page == 1
    assert chunks[0].text == "page one text"
    assert chunks[1].page == 2


def test_build_chunks_skips_blank_pages():
    chunks = build_chunks("mat-1", ["real content", "   ", "", "more content"])

    assert [c.text for c in chunks] == ["real content", "more content"]
    # Page numbers reflect original position, not post-filter index.
    assert [c.page for c in chunks] == [1, 4]


def test_build_chunks_handles_no_pages():
    assert build_chunks("mat-1", []) == []
