import pytest

from opspilot.chunking import chunk_markdown


def test_splits_by_heading():
    md = "# Title\nintro text\n## Step one\ndo this\n## Step two\ndo that"
    chunks = chunk_markdown("rb.md", md)
    assert [c.heading for c in chunks] == ["Title", "Step one", "Step two"]
    assert chunks[1].text.startswith("Step one\n")
    assert [c.index for c in chunks] == [0, 1, 2]


def test_long_section_is_windowed_with_overlap():
    body = " ".join(f"w{i}" for i in range(500))
    chunks = chunk_markdown("rb.md", f"# H\n{body}", max_words=200, overlap=50)
    assert len(chunks) == 3
    # second window starts 150 words in, so it overlaps the first by 50 words
    assert chunks[1].text.split()[1] == "w150"
    assert chunks[-1].text.split()[-1] == "w499"


def test_text_without_headings():
    chunks = chunk_markdown("plain.md", "just some text")
    assert len(chunks) == 1 and chunks[0].heading == ""


def test_empty_document():
    assert chunk_markdown("empty.md", "   ") == []


def test_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_markdown("x.md", "# a\nb", max_words=10, overlap=10)
