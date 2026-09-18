
from pathlib import Path
from typing import Any

import chromadb
import yaml
from sentence_transformers import SentenceTransformer


class RegulatoryChromaIndexer:
    """Index regulatory requirements in ChromaDB using semantic embeddings."""

    COLLECTION_NAME = "aml_regulations"
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"

    def __init__(
        self,
        source_path: str | Path,
        persist_directory: str | Path = "data/chroma",
    ):
        self.source_path = Path(source_path)
        self.persist_directory = Path(persist_directory)

        if not self.source_path.exists():
            raise FileNotFoundError(
                f"Regulatory source file not found: {self.source_path}"
            )

        self.persist_directory.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory)
        )

        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME
        )

        self.model = SentenceTransformer(self.EMBEDDING_MODEL)

    def _load_requirements(self) -> list[dict[str, Any]]:
        with self.source_path.open("r", encoding="utf-8") as file:
            content = yaml.safe_load(file) or {}

        requirements = []

        for regulation in content.get("regulations", []):
            for requirement in regulation.get("requirements", []):
                requirements.append(
                    {
                        "regulation_id": regulation.get("regulation_id"),
                        "title": regulation.get("title"),
                        "jurisdiction": regulation.get("jurisdiction"),
                        "source": regulation.get("source"),
                        "source_document": regulation.get("source_document"),
                        "requirement_id": requirement.get("requirement_id"),
                        "topic": requirement.get("topic"),
                        "text": requirement.get("text", "").strip(),
                        "applicability": requirement.get(
                            "applicability", []
                        ),
                    }
                )

        return requirements

    def index(self) -> dict[str, int]:
        requirements = self._load_requirements()

        if not requirements:
            return {
                "indexed": 0,
                "collection_count": self.collection.count(),
            }

        ids = []
        documents = []
        metadatas = []

        for requirement in requirements:
            requirement_id = requirement["requirement_id"]

            applicability = requirement["applicability"]

            metadata = {
                "regulation_id": requirement["regulation_id"] or "",
                "title": requirement["title"] or "",
                "jurisdiction": requirement["jurisdiction"] or "",
                "source": requirement["source"] or "",
                "source_document": requirement["source_document"] or "",
                "requirement_id": requirement_id or "",
                "topic": requirement["topic"] or "",
                "applicability": ",".join(applicability),
            }

            ids.append(requirement_id)
            documents.append(requirement["text"])
            metadatas.append(metadata)

        embeddings = self.model.encode(documents).tolist()

        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        return {
            "indexed": len(documents),
            "collection_count": self.collection.count(),
        }

    def search(
        self,
        query: str,
        *,
        max_results: int = 5,
    ) -> list[dict[str, Any]]:
        if not query or not query.strip():
            return []

        query_embedding = self.model.encode(
            [query.strip()]
        ).tolist()

        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=max_results,
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        ids = results.get("ids", [[]])[0]

        matches = []

        for index, document in enumerate(documents):
            matches.append(
                {
                    "requirement_id": ids[index],
                    "text": document,
                    "metadata": metadatas[index],
                    "distance": distances[index],
                }
            )

        return matches
