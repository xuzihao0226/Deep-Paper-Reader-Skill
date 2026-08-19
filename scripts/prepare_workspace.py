#!/usr/bin/env python3
"""Prepare a durable workspace for one academic paper."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


ARXIV_ID_RE = re.compile(r"(?<!\d)(\d{4}\.\d{4,5})(?:v\d+)?(?!\d)", re.I)
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.I)
VALID_MODES = ("quick_read", "deep_read", "critical_review")
VALID_ACCESS_LEVELS = ("full_text", "partial_text", "abstract_only", "unknown")


def classify_input(value: str) -> dict[str, str | None]:
    """Classify a paper input without performing network access."""
    candidate = value.strip()
    path = Path(candidate).expanduser()
    if path.is_file() and path.suffix.lower() == ".pdf":
        return {"input_type": "local_pdf", "normalized_input": str(path.resolve()), "identifier": None}

    arxiv_match = ARXIV_ID_RE.search(candidate)
    if arxiv_match and ("arxiv" in candidate.lower() or candidate == arxiv_match.group(0)):
        arxiv_id = arxiv_match.group(1)
        return {"input_type": "arxiv", "normalized_input": arxiv_id, "identifier": arxiv_id}

    lowered = candidate.lower()
    doi_value = candidate
    if lowered.startswith("doi:"):
        doi_value = candidate[4:].strip()
    elif "doi.org/" in lowered:
        doi_value = candidate.split("doi.org/", 1)[1].strip()
    if DOI_RE.match(doi_value):
        return {"input_type": "doi", "normalized_input": doi_value, "identifier": doi_value}

    parsed = urlparse(candidate)
    if parsed.scheme in {"http", "https"}:
        is_pdf = parsed.path.lower().endswith(".pdf") or "pdf" in parsed.query.lower()
        return {
            "input_type": "direct_pdf_url" if is_pdf else "web_page",
            "normalized_input": candidate,
            "identifier": None,
        }

    return {"input_type": "paper_title", "normalized_input": candidate, "identifier": None}


def safe_slug(value: str, fallback_seed: str, max_length: int = 80) -> str:
    """Create a cross-platform directory name while retaining readable Unicode."""
    normalized = unicodedata.normalize("NFKC", value).strip()
    normalized = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", " ", normalized)
    normalized = re.sub(r"\s+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-. ")
    if normalized:
        return normalized[:max_length].rstrip("-. ")
    digest = hashlib.sha256(fallback_seed.encode("utf-8")).hexdigest()[:10]
    return f"paper-{digest}"


def fill_known_template_fields(template: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def prepare_workspace(args: argparse.Namespace) -> dict[str, object]:
    classified = classify_input(args.paper)
    title = args.title.strip() if args.title else str(classified["normalized_input"])
    slug = safe_slug(args.workspace_name or title, args.paper)
    output_root = Path(args.output_root).expanduser().resolve()
    workspace = output_root / slug
    report_path = workspace / "report.md"
    metadata_path = workspace / "metadata.json"

    if report_path.exists() and not args.force:
        raise FileExistsError(
            f"Refusing to overwrite existing report: {report_path}. "
            "Use --force only after confirming replacement is intended."
        )

    for directory in (workspace, workspace / "source", workspace / "images", workspace / "evidence"):
        directory.mkdir(parents=True, exist_ok=True)

    source_copy = None
    if classified["input_type"] == "local_pdf":
        original = Path(str(classified["normalized_input"]))
        source_copy = workspace / "source" / "paper.pdf"
        if original.resolve() != source_copy.resolve():
            shutil.copy2(original, source_copy)

    skill_root = Path(__file__).resolve().parents[1]
    template_path = Path(args.template).expanduser().resolve() if args.template else skill_root / "assets" / "report-template.md"
    if not template_path.is_file():
        raise FileNotFoundError(f"Report template not found: {template_path}")

    template = template_path.read_text(encoding="utf-8")
    initial_report = fill_known_template_fields(
        template,
        {
            "paper_title": title,
            "reading_mode": args.mode,
            "primary_paper_type": args.paper_type,
            "secondary_paper_types": "",
            "access_level": args.access_level,
            "report_language": args.language,
            "authors": args.authors or "To be resolved",
            "year": args.year or "To be resolved",
            "venue_or_source": "To be resolved",
            "doi": str(classified["identifier"]) if classified["input_type"] == "doi" else "Not provided",
            "arxiv_id": str(classified["identifier"]) if classified["input_type"] == "arxiv" else "Not provided",
            "source_url": args.source_url or (args.paper if classified["input_type"] in {"direct_pdf_url", "web_page"} else "Not provided"),
            "full_text_read": "No — workspace preparation only",
            "extraction_limitations": "Source extraction has not run yet.",
        },
    )
    report_path.write_text(initial_report, encoding="utf-8")

    metadata = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "paper": {
            "title": title,
            "authors": [item.strip() for item in (args.authors or "").split(";") if item.strip()],
            "year": args.year,
            "input": args.paper,
            "input_type": classified["input_type"],
            "normalized_input": classified["normalized_input"],
            "identifier": classified["identifier"],
            "source_url": args.source_url,
        },
        "reading": {
            "mode": args.mode,
            "language": args.language,
            "primary_paper_type": args.paper_type,
            "paper_type_confidence": "unclassified" if args.paper_type == "unclassified" else "user_supplied",
            "access_level": args.access_level,
        },
        "extraction": {
            "status": "not_started",
            "source_copy": str(source_copy.relative_to(workspace)) if source_copy else None,
            "limitations": [],
        },
        "assumptions": [],
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "workspace": str(workspace),
        "report": str(report_path),
        "metadata": str(metadata_path),
        "input_type": classified["input_type"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", required=True, help="Local PDF, PDF URL, arXiv link/ID, DOI, publisher page, or paper title")
    parser.add_argument("--output-root", default=".", help="Parent directory for the paper workspace")
    parser.add_argument("--workspace-name", help="Optional explicit workspace directory name")
    parser.add_argument("--title", help="Known paper title")
    parser.add_argument("--authors", help="Semicolon-separated author names")
    parser.add_argument("--year", help="Publication year")
    parser.add_argument("--source-url", help="Authoritative source URL when different from --paper")
    parser.add_argument("--mode", choices=VALID_MODES, default="deep_read")
    parser.add_argument("--paper-type", default="unclassified")
    parser.add_argument("--access-level", choices=VALID_ACCESS_LEVELS, default="unknown")
    parser.add_argument("--language", default="follow_user")
    parser.add_argument("--template", help="Optional report template path")
    parser.add_argument("--force", action="store_true", help="Replace an existing report after explicit confirmation")
    return parser


def main() -> int:
    try:
        result = prepare_workspace(build_parser().parse_args())
    except (FileExistsError, FileNotFoundError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
