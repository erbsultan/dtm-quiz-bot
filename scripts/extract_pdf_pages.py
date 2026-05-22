#!/usr/bin/env python3
import argparse
from pathlib import Path


def parse_page_range(value: str) -> tuple[int, int]:
    if "-" in value:
        start_raw, end_raw = value.split("-", maxsplit=1)
    else:
        start_raw = end_raw = value

    try:
        start = int(start_raw)
        end = int(end_raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Pages must be numbers, for example 142-145.") from exc

    if start < 1 or end < 1:
        raise argparse.ArgumentTypeError("Book page numbers must be positive.")
    if end < start:
        raise argparse.ArgumentTypeError("End page must be greater than or equal to start page.")
    return start, end


def extract_pdf_pages(input_path: Path, pages: tuple[int, int], output_path: Path, offset: int = 0) -> None:
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError as exc:
        raise RuntimeError("pypdf is not installed. Run: pip install -r requirements.txt") from exc

    if not input_path.exists():
        raise FileNotFoundError(f"Input PDF not found: {input_path}")
    if input_path.suffix.lower() != ".pdf":
        raise ValueError("Input file must be a PDF.")

    reader = PdfReader(str(input_path))
    writer = PdfWriter()
    start_page, end_page = pages

    for book_page in range(start_page, end_page + 1):
        pdf_index = book_page + offset - 1
        if pdf_index < 0 or pdf_index >= len(reader.pages):
            raise IndexError(
                f"Book page {book_page} with offset {offset} maps to PDF index {pdf_index}, "
                f"but the PDF has {len(reader.pages)} pages."
            )
        writer.add_page(reader.pages[pdf_index])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as output_file:
        writer.write(output_file)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract a book page range into a separate PDF excerpt.")
    parser.add_argument("--input", required=True, type=Path, help="Input PDF path.")
    parser.add_argument("--pages", required=True, type=parse_page_range, help="Book page range, for example 142-145.")
    parser.add_argument("--output", required=True, type=Path, help="Output excerpt PDF path.")
    parser.add_argument("--offset", default=0, type=int, help="PDF index offset. Example: --offset -2.")
    args = parser.parse_args()

    try:
        extract_pdf_pages(args.input, args.pages, args.output, args.offset)
    except Exception as exc:
        raise SystemExit(f"Error: {exc}") from exc


if __name__ == "__main__":
    main()
