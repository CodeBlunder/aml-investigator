
from pathlib import Path

from app.retrieval.chroma_indexer import RegulatoryChromaIndexer


BASE_DIR = Path(__file__).resolve().parent.parent

SOURCE_PATH = (
    BASE_DIR
    / "data"
    / "understanding"
    / "regulations"
    / "aml_requirements.yaml"
)

CHROMA_PATH = BASE_DIR / "data" / "chroma"


def get_indexer():
    return RegulatoryChromaIndexer(
        source_path=SOURCE_PATH,
        persist_directory=CHROMA_PATH,
    )


def test_structuring_query_retrieves_structuring_requirement():
    indexer = get_indexer()

    results = indexer.search(
        "multiple transactions below a threshold in a short period may indicate structuring",
        max_results=5,
    )

    assert results

    requirement_ids = {
        result["requirement_id"]
        for result in results
    }

    assert "RBI-KYC-2016-R1" in requirement_ids


def test_transaction_monitoring_query_retrieves_monitoring_requirement():
    indexer = get_indexer()

    results = indexer.search(
        "monitor transactions for suspicious or unusual activity",
        max_results=5,
    )

    assert results

    requirement_ids = {
        result["requirement_id"]
        for result in results
    }

    assert "RBI-KYC-2016-R1" in requirement_ids


def test_sanctions_query_does_not_require_unrelated_rbi_requirement():
    indexer = get_indexer()

    results = indexer.search(
        "sanctions watchlist screening",
        max_results=5,
    )

    assert results

    for result in results:
        assert result["requirement_id"] != "AML-PROTOTYPE-001-R5"


def test_regulatory_metadata_is_returned():
    indexer = get_indexer()

    results = indexer.search(
        "evidence supporting an AML investigation",
        max_results=3,
    )

    assert results

    metadata = results[0]["metadata"]

    assert "regulation_id" in metadata
    assert "requirement_id" in metadata
    assert "source_document" in metadata
    assert "topic" in metadata
    assert "applicability" in metadata
