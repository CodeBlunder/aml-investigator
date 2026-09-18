
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


def main():
    indexer = RegulatoryChromaIndexer(
        source_path=SOURCE_PATH,
        persist_directory=CHROMA_PATH,
    )

    result = indexer.index()

    print("Regulatory indexing complete.")
    print(f"Indexed requirements: {result['indexed']}")
    print(f"Collection count: {result['collection_count']}")


if __name__ == "__main__":
    main()
