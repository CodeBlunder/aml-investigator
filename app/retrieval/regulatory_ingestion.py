
from dataclasses import dataclass
from pathlib import Path
import re

import pymupdf


@dataclass
class RegulatoryChunk:
    document: str
    page: int
    section: str | None
    subsection: str | None
    text: str


def extract_pdf_text(pdf_path: str | Path) -> list[dict]:
    """Extract text from a regulatory PDF while preserving page boundaries."""

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages = []

    with pymupdf.open(pdf_path) as document:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text").strip()

            if not text:
                continue

            pages.append(
                {
                    "document": pdf_path.name,
                    "page": page_number,
                    "text": text,
                }
            )

    return pages


def chunk_regulatory_pages(
    pages: list[dict],
) -> list[RegulatoryChunk]:
    """
    Convert extracted regulatory pages into hierarchy-aware chunks.

    Section headings are detected conservatively from common regulatory
    heading patterns. Page boundaries are always preserved.
    """

    chunks: list[RegulatoryChunk] = []

    current_section: str | None = None
    current_subsection: str | None = None

    for page in pages:
        document = page["document"]
        page_number = page["page"]
        text = page["text"]

        paragraphs = [
            paragraph.strip()
            for paragraph in text.split("\n\n")
            if paragraph.strip()
        ]

        for paragraph in paragraphs:
            lines = [
                line.strip()
                for line in paragraph.splitlines()
                if line.strip()
            ]

            if not lines:
                continue

            first_line = lines[0]

            # Check subsection before section because
            # "1.1 Something" also begins with "1."
            if _is_subsection_heading(first_line):
                current_subsection = first_line

                if len(lines) > 1:
                    chunks.append(
                        RegulatoryChunk(
                            document=document,
                            page=page_number,
                            section=current_section,
                            subsection=current_subsection,
                            text="\n".join(lines[1:]),
                        )
                    )

                continue

            if _is_section_heading(first_line):
                current_section = first_line
                current_subsection = None

                if len(lines) > 1:
                    chunks.append(
                        RegulatoryChunk(
                            document=document,
                            page=page_number,
                            section=current_section,
                            subsection=None,
                            text="\n".join(lines[1:]),
                        )
                    )

                continue

            chunks.append(
                RegulatoryChunk(
                    document=document,
                    page=page_number,
                    section=current_section,
                    subsection=current_subsection,
                    text=paragraph,
                )
            )

    return chunks


def _is_section_heading(line: str) -> bool:
    """Return True for simple numbered regulatory section headings."""

    return bool(
        re.match(
            r"^\d+\s*[.)]\s+\S+",
            line,
        )
    )


def _is_subsection_heading(line: str) -> bool:
    """Return True for numbered subsection headings."""

    return bool(
        re.match(
            r"^\d+\.\d+\s*[.)]?\s+\S+",
            line,
        )
    )
