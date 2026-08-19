#!/usr/bin/env python3
"""Extract traceable page and block text from a paper PDF."""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz


MIN_READABLE_CHARS = 50
HEADING_NUMBER_RE = re.compile(r"^(?:\d+(?:\.\d+)*|[IVXLC]+)\s*[.)]?\s+\S+")
PAGE_NUMBER_RE = re.compile(r"^(?:page\s*)?\d{1,4}$", re.I)
STANDALONE_HEADING_RE = re.compile(
    r"^(?:abstract|introduction|background|discussion|conclusion|notes?|references|bibliography|appendix|"
    r"摘要|引言|绪论|讨论|结论|注释|参考文献|附录)$",
    re.I,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in value.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def margin_key(text: str) -> str:
    normalized = normalize_text(text).lower()
    normalized = re.sub(r"\b\d+\b", "#", normalized)
    return normalized


def extract_page_blocks(page: fitz.Page) -> list[dict[str, Any]]:
    page_dict = page.get_text("dict", sort=True)
    blocks = []
    for raw_block in page_dict.get("blocks", []):
        if raw_block.get("type") != 0:
            continue
        lines = []
        spans = []
        for raw_line in raw_block.get("lines", []):
            line_text = "".join(span.get("text", "") for span in raw_line.get("spans", []))
            line_text = re.sub(r"\s+", " ", line_text).strip()
            if line_text:
                lines.append(line_text)
            spans.extend(raw_line.get("spans", []))
        text = normalize_text("\n".join(lines))
        if not text:
            continue
        bbox = [round(float(value), 2) for value in raw_block.get("bbox", (0, 0, 0, 0))]
        sizes = [float(span.get("size", 0)) for span in spans if span.get("text", "").strip()]
        flags = [int(span.get("flags", 0)) for span in spans if span.get("text", "").strip()]
        blocks.append(
            {
                "text": text,
                "bbox": bbox,
                "font_size_max": round(max(sizes), 2) if sizes else 0,
                "font_size_median": round(statistics.median(sizes), 2) if sizes else 0,
                "bold_ratio": round(sum(1 for flag in flags if flag & 16) / len(flags), 3) if flags else 0,
            }
        )
    return blocks


def identify_repeated_margins(pages: list[dict[str, Any]]) -> set[str]:
    counts: Counter[str] = Counter()
    page_count = len(pages)
    # Journals often alternate author and article-title headers on odd/even pages.
    # A 35% threshold removes either alternating header while still requiring
    # recurrence across a substantial part of the document.
    threshold = max(2, math.ceil(page_count * 0.35))
    for page in pages:
        height = page["height"]
        seen_on_page = set()
        for block in page["blocks"]:
            top = block["bbox"][1]
            bottom = block["bbox"][3]
            in_margin = top <= height * 0.1 or bottom >= height * 0.9
            key = margin_key(block["text"])
            if in_margin and key and len(key) <= 180:
                seen_on_page.add(key)
        counts.update(seen_on_page)
    return {key for key, count in counts.items() if count >= threshold}


def document_body_font_size(pages: list[dict[str, Any]]) -> float:
    sizes = []
    for page in pages:
        for block in page["blocks"]:
            size = block["font_size_median"]
            if size > 0 and len(block["text"]) >= 40:
                sizes.append(size)
    if not sizes:
        sizes = [
            block["font_size_median"]
            for page in pages
            for block in page["blocks"]
            if block["font_size_median"] > 0
        ]
    return round(statistics.median(sizes), 2) if sizes else 0


def is_heading_candidate(block: dict[str, Any], body_size: float) -> bool:
    text = block["text"].replace("\n", " ").strip()
    if not text or len(text) > 180 or len(text.split()) > 24:
        return False
    if re.match(r"^(?:https?://|www\.)", text, flags=re.I):
        return False
    math_symbols = sum(text.count(symbol) for symbol in ("=", "+", "−", "*", "(", ")", "[", "]", "∑"))
    if math_symbols >= 2 and not re.search(r"[A-Za-z]{3,}", text):
        return False
    if PAGE_NUMBER_RE.fullmatch(text):
        return False
    numbered = bool(HEADING_NUMBER_RE.match(text))
    numbered_title = numbered and (
        body_size <= 0
        or block["font_size_max"] >= body_size * 1.05
    )
    if numbered and body_size > 0 and block["font_size_max"] < body_size * 1.05:
        return False
    clearly_larger = body_size > 0 and block["font_size_max"] >= body_size * 1.3
    bold_short = block["bold_ratio"] >= 0.6 and len(text) <= 120
    standalone_heading = bool(STANDALONE_HEADING_RE.fullmatch(text))
    sentence_like = text.endswith((".", "。", ";", "；"))
    return numbered_title or clearly_larger or standalone_heading or (bold_short and not sentence_like)


def classify_page_status(blocks: list[dict[str, Any]], image_count: int) -> tuple[str, int]:
    raw_text = "\n".join(block["text"] for block in blocks)
    char_count = len(re.sub(r"\s+", "", raw_text))
    if char_count >= MIN_READABLE_CHARS:
        return "readable", char_count
    only_page_numbers = bool(blocks) and all(
        PAGE_NUMBER_RE.fullmatch(normalize_text(block.get("text", ""))) for block in blocks
    )
    if image_count == 0 and (not blocks or only_page_numbers):
        return "blank_or_divider", char_count
    return "low_text", char_count


def private_use_count(text: str) -> int:
    return sum(1 for char in text if "\ue000" <= char <= "\uf8ff")


def build_markdown(pages: list[dict[str, Any]], source_name: str) -> str:
    lines = [f"# Extracted Text — {source_name}", "", "> Stable locators use `P###-B###`.", ""]
    for page in pages:
        lines.extend([f"## PDF Page {page['pdf_page']}", ""])
        if page["status"] == "low_text":
            lines.extend([f"> Extraction status: {page['status']}. OCR may be required.", ""])
        elif page["status"] == "blank_or_divider":
            lines.extend(["> Intentionally sparse or blank page.", ""])
        for block in page["blocks"]:
            if block.get("removed_as_repeated_margin"):
                continue
            locator = block["block_id"]
            text = block["text"]
            lines.append(f"<!-- {locator} -->")
            if block["heading_candidate"]:
                lines.append(f"### {text.replace(chr(10), ' ')}")
            else:
                lines.append(text)
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def update_metadata(workspace: Path, summary: dict[str, Any]) -> None:
    metadata_path = workspace / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    extraction = metadata.setdefault("extraction", {})
    extraction.update(
        {
            "status": summary["status"],
            "text_markdown": "evidence/fulltext.md",
            "pages_json": "evidence/pages.json",
            "summary_json": "evidence/extraction.json",
            "page_count": summary["page_count"],
            "readable_page_count": summary["readable_page_count"],
            "ocr_candidate_pages": summary["ocr_candidate_pages"],
            "limitations": summary["limitations"],
        }
    )
    metadata["reading"]["access_level"] = summary["access_level"]
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def extract_workspace(workspace: Path, keep_repeated_margins: bool = False) -> dict[str, Any]:
    metadata_path = workspace / "metadata.json"
    pdf_path = workspace / "source" / "paper.pdf"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"metadata.json not found: {metadata_path}")
    if not pdf_path.is_file():
        raise FileNotFoundError(f"paper PDF not found: {pdf_path}")

    evidence_dir = workspace / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    pages = []
    with fitz.open(pdf_path) as document:
        if document.needs_pass:
            raise ValueError("The PDF is password protected and cannot be extracted without authorization.")
        for page_index, page in enumerate(document):
            blocks = extract_page_blocks(page)
            image_count = len(page.get_images(full=True))
            status, char_count = classify_page_status(blocks, image_count)
            pages.append(
                {
                    "pdf_page": page_index + 1,
                    "width": round(page.rect.width, 2),
                    "height": round(page.rect.height, 2),
                    "char_count": char_count,
                    "image_count": image_count,
                    "status": status,
                    "blocks": blocks,
                }
            )

    repeated = set() if keep_repeated_margins else identify_repeated_margins(pages)
    body_size = document_body_font_size(pages)
    for page in pages:
        for block_index, block in enumerate(page["blocks"], start=1):
            block["block_id"] = f"P{page['pdf_page']:03d}-B{block_index:03d}"
            block["heading_candidate"] = is_heading_candidate(block, body_size)
            block["removed_as_repeated_margin"] = margin_key(block["text"]) in repeated

    readable_pages = [page["pdf_page"] for page in pages if page["status"] == "readable"]
    blank_pages = [page["pdf_page"] for page in pages if page["status"] == "blank_or_divider"]
    ocr_pages = [
        page["pdf_page"]
        for page in pages
        if page["status"] == "low_text" and page["image_count"] > 0
    ]
    low_text_pages = [page["pdf_page"] for page in pages if page["status"] == "low_text"]
    page_count = len(pages)
    if page_count == 0 or not readable_pages:
        status = "needs_ocr"
        access_level = "partial_text"
    elif low_text_pages:
        status = "partial_text_ready"
        access_level = "partial_text"
    else:
        status = "text_ready"
        access_level = "full_text"

    all_text = "\n".join(
        block["text"]
        for page in pages
        for block in page["blocks"]
        if not block.get("removed_as_repeated_margin")
    )
    limitations = []
    if low_text_pages:
        limitations.append(f"Low extracted text on PDF pages: {', '.join(map(str, low_text_pages))}")
    if ocr_pages:
        limitations.append(f"OCR candidates: PDF pages {', '.join(map(str, ocr_pages))}")
    replacement_count = all_text.count("\ufffd")
    private_count = private_use_count(all_text)
    if replacement_count:
        limitations.append(f"Unicode replacement characters detected: {replacement_count}")
    if private_count:
        limitations.append(f"Private-use glyphs detected: {private_count}")

    summary = {
        "schema_version": 1,
        "extracted_at": utc_now(),
        "status": status,
        "access_level": access_level,
        "page_count": page_count,
        "readable_page_count": len(readable_pages),
        "blank_or_divider_pages": blank_pages,
        "low_text_pages": low_text_pages,
        "ocr_candidate_pages": ocr_pages,
        "body_font_size": body_size,
        "repeated_margin_patterns_removed": sorted(repeated),
        "block_count": sum(len(page["blocks"]) for page in pages),
        "character_count": len(all_text),
        "replacement_character_count": replacement_count,
        "private_use_character_count": private_count,
        "limitations": limitations,
    }

    (evidence_dir / "pages.json").write_text(
        json.dumps({"schema_version": 1, "pages": pages}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (evidence_dir / "extraction.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (evidence_dir / "fulltext.md").write_text(build_markdown(pages, pdf_path.name), encoding="utf-8")
    update_metadata(workspace, summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, help="Paper workspace containing source/paper.pdf")
    parser.add_argument(
        "--keep-repeated-margins",
        action="store_true",
        help="Keep repeated headers and footers in extracted text",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        summary = extract_workspace(
            Path(args.workspace).expanduser().resolve(),
            keep_repeated_margins=args.keep_repeated_margins,
        )
    except (FileNotFoundError, ValueError, OSError, fitz.FileDataError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
