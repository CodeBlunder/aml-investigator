from pathlib import Path

from app.retrieval.regulatory_retriever import RegulatoryRetriever


REGULATORY_FILE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "understanding"
    / "regulations"
    / "aml_requirements.yaml"
)


def test_regulatory_file_loads():
    retriever = RegulatoryRetriever(REGULATORY_FILE)

    assert len(retriever.regulations) >= 1


def test_transaction_monitoring_retrieval():
    retriever = RegulatoryRetriever(REGULATORY_FILE)

    results = retriever.search(
        "transaction monitoring suspicious transaction"
    )

    assert results
    assert any(
        result["requirement_id"]
        == "AML-PROTOTYPE-001-R1"
        for result in results
    )


def test_structuring_retrieval():
    retriever = RegulatoryRetriever(REGULATORY_FILE)

    results = retriever.search(
        "multiple transactions short period threshold",
        applicability="structuring",
    )

    assert results
    assert results[0]["requirement_id"] == "AML-PROTOTYPE-001-R2"


def test_sanctions_retrieval():
    retriever = RegulatoryRetriever(REGULATORY_FILE)

    results = retriever.search(
        "sanctions probable partial match",
        applicability="sanctions",
    )

    assert results
    assert results[0]["requirement_id"] == "AML-PROTOTYPE-001-R5"


def test_empty_query_returns_no_results():
    retriever = RegulatoryRetriever(REGULATORY_FILE)

    assert retriever.search("") == []