#!/usr/bin/env python3
"""
Extract readable content from webpages for ingestion by the article generator.

Usage:
    python3 .pi/skills/ingest-content/extract_webpage.py <url> [--output <output-path>]

Uses readability-lxml or newspaper3k to strip navigation, ads, and boilerplate.
Falls back to basic HTML extraction if those aren't installed.
"""

import sys
import os
import re
import argparse
from datetime import datetime


def extract_readability(url: str) -> dict:
    """Extract using readability-lxml."""
    from readability import Document
    import requests

    resp = requests.get(url, timeout=30, headers={
        "User-Agent": "Mozilla/5.0 (compatible; ArticleExtractor/1.0)"
    })
    resp.raise_for_status()
    doc = Document(resp.text)
    title = doc.title()
    content_html = doc.summary()
    # Simple HTML to text conversion
    content = re.sub(r'<[^>]+>', '', content_html)
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = content.strip()
    return {"title": title, "content": content, "url": url}


def extract_newspaper(url: str) -> dict:
    """Extract using newspaper3k."""
    from newspaper import Article

    article = Article(url)
    article.download()
    article.parse()
    return {
        "title": article.title,
        "content": article.text,
        "url": url,
        "authors": article.authors,
        "publish_date": str(article.publish_date) if article.publish_date else "Unknown",
    }


def extract_basic(url: str) -> dict:
    """Basic fallback using requests and minimal HTML stripping."""
    import requests
    from html.parser import HTMLParser

    class TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.text_parts = []
            self.skip = False

        def handle_starttag(self, tag, attrs):
            if tag in ('script', 'style', 'nav', 'header', 'footer', 'aside'):
                self.skip = True

        def handle_endtag(self, tag):
            if tag in ('script', 'style', 'nav', 'header', 'footer', 'aside'):
                self.skip = False
            if tag in ('p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'div'):
                self.text_parts.append('\n')

        def handle_data(self, data):
            if not self.skip:
                text = data.strip()
                if text:
                    self.text_parts.append(text + ' ')

    resp = requests.get(url, timeout=30, headers={
        "User-Agent": "Mozilla/5.0 (compatible; ArticleExtractor/1.0)"
    })
    resp.raise_for_status()

    parser = TextExtractor()
    parser.feed(resp.text)
    text = ''.join(parser.text_parts)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    text = text.strip()

    # Extract title from HTML title tag
    title_match = re.search(r'<title[^>]*>(.*?)</title>', resp.text, re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else "Unknown"

    return {"title": title, "content": text, "url": url}


def main():
    parser = argparse.ArgumentParser(description="Extract readable content from webpages")
    parser.add_argument("url", help="URL of the webpage to extract")
    parser.add_argument("--output", "-o", help="Output file path")
    args = parser.parse_args()

    result = None
    lib_used = None
    errors = []

    for lib_name, extract_fn in [
        ("readability-lxml", extract_readability),
        ("newspaper3k", extract_newspaper),
        ("basic HTML", extract_basic),
    ]:
        try:
            result = extract_fn(args.url)
            lib_used = lib_name
            break
        except ImportError:
            errors.append(f"{lib_name} not installed")
            continue
        except Exception as e:
            errors.append(f"{lib_name} failed: {e}")
            continue

    if result is None:
        print(
            f"Error: Could not extract webpage. Tried: {'; '.join(errors)}",
            file=sys.stderr,
        )
        sys.exit(1)

    output = f"""# Source: {result.get('title', 'Webpage')}

## Metadata
- Type: Webpage
- URL: {args.url}
- Extracted with: {lib_used}
- Date extracted: {datetime.now().isoformat()}
{"- Authors: " + ", ".join(result.get('authors', [])) if result.get('authors') else ""}
{"- Published: " + result.get('publish_date', '') if result.get('publish_date') else ""}

## Content

{result['content']}
"""
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Extracted webpage saved to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
