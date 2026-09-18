from pathlib import Path

from app.retrieval.regulatory_ingestion import extract_pdf_text


def test_missing_pdf_raises_error(tmp_path):
    missing_pdf = tmp_path / "missing.pdf"

    try:
        extract_pdf_text(missing_pdf)
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError:
        pass

from app.retrieval.regulatory_ingestion import (
    RegulatoryChunk,
    chunk_regulatory_pages,
)


def test_regulatory_chunk_preserves_page_and_section():
    pages = [
        {
            "document": "aml.pdf",
            "page": 4,
            "text": (
                "1. Customer Due Diligence\n\n"
                "Financial institutions must identify customers."
            ),
        }
    ]

    chunks = chunk_regulatory_pages(pages)

    assert len(chunks) == 1
    assert isinstance(chunks[0], RegulatoryChunk)
    assert chunks[0].document == "aml.pdf"
    assert chunks[0].page == 4
    assert chunks[0].section == "1. Customer Due Diligence"
    assert chunks[0].subsection is None
    assert "identify customers" in chunks[0].text


def test_regulatory_chunk_preserves_subsection():
    pages = [
        {
            "document": "aml.pdf",
            "page": 5,
            "text": (
                "1. Customer Due Diligence\n\n"
                "1.1 Customer Identification\n\n"
                "Institutions must identify and verify customers."
            ),
        }
    ]

    chunks = chunk_regulatory_pages(pages)

    assert len(chunks) == 1
    assert chunks[0].section == "1. Customer Due Diligence"
    assert chunks[0].subsection == "1.1 Customer Identification"
    assert "identify and verify" in chunks[0].text


def test_regulatory_chunk_preserves_multiple_paragraphs():
    pages = [
        {
            "document": "aml.pdf",
            "page": 6,
            "text": (
                "Institutions must monitor transactions.\n\n"
                "Institutions must investigate relevant alerts."
            ),
        }
    ]

    chunks = chunk_regulatory_pages(pages)

    assert len(chunks) == 2
    assert chunks[0].page == 6
    assert chunks[1].page == 6



from pathlib import Path

from app.retrieval.regulatory_ingestion import (
    chunk_regulatory_pages,
    extract_pdf_text,
)


FIXTURE_PDF = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "sample_aml_regulation.pdf"
)


def test_real_pdf_is_extracted():
    pages = extract_pdf_text(FIXTURE_PDF)

    assert len(pages) == 2
    assert pages[0]["page"] == 1
    assert pages[1]["page"] == 2
    assert "Customer Due Diligence" in pages[0]["text"]
    assert "Transaction Monitoring" in pages[1]["text"]


def test_real_pdf_produces_regulatory_chunks():
    pages = extract_pdf_text(FIXTURE_PDF)
    chunks = chunk_regulatory_pages(pages)

    assert len(chunks) == 2

    assert chunks[0].document == "sample_aml_regulation.pdf"
    assert chunks[0].page == 1
    assert chunks[0].section == "1. Customer Due Diligence"
    assert "identify and verify customers" in chunks[0].text

    assert chunks[1].page == 2
    assert chunks[1].section == "2. Transaction Monitoring"
    assert "monitor transactions" in chunks[1].text