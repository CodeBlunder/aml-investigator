from pathlib import Path
from typing import Any

import yaml


class RegulatoryRetriever:
    """Retrieve regulatory requirements from the regulatory understanding layer."""

    def __init__(self, source_path: str | Path):
        self.source_path = Path(source_path)

        if not self.source_path.exists():
            raise FileNotFoundError(
                f"Regulatory source file not found: {self.source_path}"
            )

        with self.source_path.open("r", encoding="utf-8") as file:
            content = yaml.safe_load(file) or {}

        self.regulations = content.get("regulations", [])

    def search(
        self,
        query: str,
        *,
        applicability: str | None = None,
        max_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Return regulatory requirements relevant to the query."""

        if not query or not query.strip():
            return []

        query_terms = {
            term.strip().lower()
            for term in query.split()
            if term.strip()
        }

        results = []

        for regulation in self.regulations:
            for requirement in regulation.get("requirements", []):
                text = requirement.get("text", "")
                topic = requirement.get("topic", "")
                requirement_applicability = requirement.get(
                    "applicability", []
                )

                searchable_text = " ".join(
                    [
                        str(topic),
                        str(text),
                        " ".join(
                            str(item)
                            for item in requirement_applicability
                        ),
                    ]
                ).lower()

                if applicability:
                    if applicability.lower() not in {
                        str(item).lower()
                        for item in requirement_applicability
                    }:
                        continue

                matched_terms = sum(
                    1
                    for term in query_terms
                    if term in searchable_text
                )

                if matched_terms == 0:
                    continue

                results.append(
                    {
                        "regulation_id": regulation.get(
                            "regulation_id"
                        ),
                        "title": regulation.get("title"),
                        "jurisdiction": regulation.get(
                            "jurisdiction"
                        ),
                        "source": regulation.get("source"),
                        "source_document": regulation.get(
                            "source_document"
                        ),
                        "requirement_id": requirement.get(
                            "requirement_id"
                        ),
                        "topic": topic,
                        "text": text.strip(),
                        "applicability": requirement_applicability,
                        "matched_terms": matched_terms,
                    }
                )

        results.sort(
            key=lambda item: item["matched_terms"],
            reverse=True,
        )

        return results[:max_results]