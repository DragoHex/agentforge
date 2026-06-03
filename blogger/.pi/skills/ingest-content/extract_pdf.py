#!/usr/bin/env python3
"""
Extract text from PDF files for ingestion by the article generator.

Usage:
    python3 .pi/skills/ingest-content/extract_pdf.py <path-to-pdf> [--output <output-path>]

Outputs structured markdown: headings inferred from font size, tables as markdown,
figure/table references indexed.
"""

import sys
import os
import argparse
from datetime import datetime


def extract_pymupdf(path: str) -> str:
    """Extract with PyMuPDF: preserves headings (font size), tables (line detection), figure refs."""
    import fitz

    doc = fitz.open(path)
    all_pages = []
    figure_index = []
    table_index = []

    # Compute document-wide font size stats for heading detection
    font_sizes = []
    for page in doc:
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        for block in blocks:
            if block["type"] == 0:
                for line in block["lines"]:
                    for span in line["spans"]:
                        if span["size"] > 6:
                            font_sizes.append(span["size"])
    doc.seek(0) if hasattr(doc, "seek") else None

    if font_sizes:
        median_size = sorted(font_sizes)[len(font_sizes) // 2]
        h2_threshold = median_size * 1.35
        h3_threshold = median_size * 1.15
    else:
        h2_threshold = 14
        h3_threshold = 12

    for page_num, page in enumerate(doc, 1):
        page_lines = [f"## Page {page_num}"]

        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        for block in blocks:
            if block["type"] == 1:
                continue

            block_text_parts = []
            for line in block["lines"]:
                line_text = ""
                max_size = 0
                is_bold = False
                for span in line["spans"]:
                    line_text += span["text"]
                    if span["size"] > max_size:
                        max_size = span["size"]
                    if "bold" in span["font"].lower():
                        is_bold = True

                line_text = line_text.strip()
                if not line_text:
                    continue

                # Track figure and table references
                import re
                fig_match = re.search(r"(Figure|Fig\.?)\s+(\d+)", line_text, re.IGNORECASE)
                tbl_match = re.search(r"Table\s+(\d+)", line_text, re.IGNORECASE)
                if fig_match:
                    figure_index.append(f"Figure {fig_match.group(2)} — page {page_num}")
                if tbl_match:
                    table_index.append(f"Table {tbl_match.group(1)} — page {page_num}")

                # Apply heading markdown
                if max_size >= h2_threshold and (is_bold or len(line_text) < 80):
                    line_text = f"### {line_text}"
                elif max_size >= h3_threshold and (is_bold or len(line_text) < 80):
                    line_text = f"#### {line_text}"

                block_text_parts.append(line_text)

            if block_text_parts:
                page_lines.append("\n".join(block_text_parts))

        # Extract tables using pdfplumber for this page (more reliable table detection)
        all_pages.append("\n\n".join(page_lines))

    doc.close()

    # Build figure/table index
    index_section = ""
    if figure_index or table_index:
        index_section = "\n## Figure & Table Index\n"
        for entry in dict.fromkeys(figure_index):
            index_section += f"- {entry}\n"
        for entry in dict.fromkeys(table_index):
            index_section += f"- {entry}\n"

    return "\n\n".join(all_pages) + index_section


def extract_pdfplumber(path: str) -> str:
    """Extract with pdfplumber: preserves tables as markdown."""
    import pdfplumber

    pages = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            parts = [f"## Page {i}"]

            text = page.extract_text() or ""
            if text.strip():
                parts.append(text.strip())

            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                md_rows = []
                for j, row in enumerate(table):
                    cells = [str(c).strip() if c else "" for c in row]
                    md_rows.append("| " + " | ".join(cells) + " |")
                    if j == 0:
                        md_rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
                parts.append("\n".join(md_rows))

            pages.append("\n\n".join(parts))

    return "\n\n".join(pages)


def extract_pypdf(path: str) -> str:
    """Fallback extraction using pypdf."""
    from pypdf import PdfReader
    reader = PdfReader(path)
    pages = []
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        pages.append(f"## Page {i}\n\n{text.strip()}")
    return "\n\n".join(pages)


def main():
    parser = argparse.ArgumentParser(description="Extract text from PDF files")
    parser.add_argument("path", help="Path to the PDF file")
    parser.add_argument("--output", "-o", help="Output file path")
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"Error: File not found: {args.path}", file=sys.stderr)
        sys.exit(1)

    text = None
    lib_used = None
    errors = []

    for lib_name, fn in [
        ("PyMuPDF (fitz)", extract_pymupdf),
        ("pdfplumber", extract_pdfplumber),
        ("pypdf", extract_pypdf),
    ]:
        try:
            text = fn(args.path)
            lib_used = lib_name
            break
        except ImportError:
            errors.append(f"{lib_name} not installed")
        except Exception as e:
            errors.append(f"{lib_name} failed: {e}")

    if text is None:
        print(f"Error: Could not extract PDF. Tried: {'; '.join(errors)}", file=sys.stderr)
        sys.exit(1)

    page_count = text.count("## Page ")
    filename = os.path.basename(args.path)

    result = f"""# Source: {filename}

## Metadata
- Type: PDF
- Source: {os.path.abspath(args.path)}
- Extracted with: {lib_used}
- Date extracted: {datetime.now().isoformat()}
- Total pages: {page_count}

## Content

{text}
"""

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w") as f:
            f.write(result)
        print(f"Extracted text saved to {args.output} ({page_count} pages, {lib_used})")
    else:
        print(result)


if __name__ == "__main__":
    main()
