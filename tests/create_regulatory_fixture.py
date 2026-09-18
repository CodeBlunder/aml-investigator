
from pathlib import Path

import pymupdf


OUTPUT_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "sample_aml_regulation.pdf"
)


def create_fixture() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    document = pymupdf.open()

    page = document.new_page()
    page.insert_textbox(
        (50, 50, 550, 100),
        "1. Customer Due Diligence\n",
        fontsize=16,
    )
    page.insert_textbox(
        (50, 110, 550, 220),
        "Financial institutions must identify and verify customers "
        "using appropriate customer information.",
        fontsize=11,
    )

    page = document.new_page()
    page.insert_textbox(
        (50, 50, 550, 100),
        "2. Transaction Monitoring\n",
        fontsize=16,
    )
    page.insert_textbox(
        (50, 110, 550, 220),
        "Institutions should monitor transactions for patterns that "
        "may indicate suspicious or unusual activity.",
        fontsize=11,
    )

    document.save(OUTPUT_PATH)
    document.close()

    print(f"Created: {OUTPUT_PATH}")


if __name__ == "__main__":
    create_fixture()
