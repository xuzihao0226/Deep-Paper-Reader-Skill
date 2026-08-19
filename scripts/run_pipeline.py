#!/usr/bin/env python3
"""Run deterministic Deep Paper Reader preprocessing up to claim review."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analyze_structure import analyze_workspace
from claim_records import prepare_records
from extract_figures import extract_workspace_figures
from extract_text import extract_workspace
from fetch_source import DEFAULT_USER_AGENT, run_acquisition
from prepare_workspace import VALID_ACCESS_LEVELS, VALID_MODES, prepare_workspace


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_pipeline_summary(workspace: Path, summary: dict[str, Any]) -> None:
    evidence_dir = workspace / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "pipeline.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def create_workspace_from_args(args: argparse.Namespace) -> Path:
    prepare_args = argparse.Namespace(
        paper=args.paper,
        output_root=args.output_root,
        workspace_name=args.workspace_name,
        title=args.title,
        authors=args.authors,
        year=args.year,
        source_url=args.source_url,
        mode=args.mode,
        paper_type=args.paper_type,
        access_level=args.access_level,
        language=args.language,
        template=args.template,
        force=args.force,
    )
    return Path(prepare_workspace(prepare_args)["workspace"])


def run_pipeline(args: argparse.Namespace) -> dict[str, Any]:
    stages = []
    if args.resume_workspace:
        workspace = Path(args.resume_workspace).expanduser().resolve()
        if not (workspace / "metadata.json").is_file():
            raise FileNotFoundError(f"Cannot resume; metadata.json not found: {workspace}")
        stages.append({"stage": "prepare_workspace", "status": "reused"})
    else:
        workspace = create_workspace_from_args(args)
        stages.append({"stage": "prepare_workspace", "status": "completed"})

    summary: dict[str, Any] = {
        "schema_version": 1,
        "started_at": utc_now(),
        "workspace": str(workspace),
        "status": "running",
        "stages": stages,
    }
    write_pipeline_summary(workspace, summary)

    try:
        acquisition = run_acquisition(workspace, args.timeout, args.user_agent)
        stages.append({"stage": "fetch_source", "status": acquisition["status"], "details": acquisition})
        if acquisition["status"] != "full_text_ready":
            summary.update(
                {
                    "finished_at": utc_now(),
                    "status": "needs_source",
                    "next_action": "Resolve an authoritative readable source, then resume the workspace.",
                }
            )
            write_pipeline_summary(workspace, summary)
            return summary

        extraction = extract_workspace(workspace, keep_repeated_margins=args.keep_repeated_margins)
        stages.append({"stage": "extract_text", "status": extraction["status"], "details": extraction})
        if extraction["status"] == "needs_ocr":
            summary.update(
                {
                    "finished_at": utc_now(),
                    "status": "needs_ocr",
                    "next_action": "Run authorized OCR on the listed pages, then resume extraction.",
                }
            )
            write_pipeline_summary(workspace, summary)
            return summary

        structure = analyze_workspace(workspace, args.max_candidates)
        stages.append({"stage": "analyze_structure", "status": "completed", "details": structure})

        figures = extract_workspace_figures(workspace)
        stages.append(
            {
                "stage": "extract_figures",
                "status": "completed" if figures["figures"] else "no_source_figures",
                "details": {"figure_count": len(figures["figures"]), "note": figures["note"]},
            }
        )

        claims_path = workspace / "evidence" / "claims.json"
        if claims_path.exists():
            stages.append({"stage": "prepare_claim_review", "status": "reused_existing"})
        elif structure["claim_candidate_count"] > 0:
            claim_result = prepare_records(workspace)
            stages.append({"stage": "prepare_claim_review", "status": "completed", "details": claim_result})
        else:
            stages.append({"stage": "prepare_claim_review", "status": "manual_review_required_no_candidates"})

        status = "ready_for_claim_review" if structure["claim_candidate_count"] > 0 else "ready_for_manual_claim_review"
        summary.update(
            {
                "finished_at": utc_now(),
                "status": status,
                "next_action": (
                    "Review evidence/claims.json, validate claim records, write report.md, then run final report validation."
                    if claims_path.exists() or structure["claim_candidate_count"] > 0
                    else "Review evidence/reading-map.md and create central claim records manually."
                ),
            }
        )
    except Exception as exc:
        stages.append({"stage": "pipeline", "status": "failed", "error": str(exc)})
        summary.update({"finished_at": utc_now(), "status": "failed", "error": str(exc)})
        write_pipeline_summary(workspace, summary)
        raise

    write_pipeline_summary(workspace, summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--paper", help="Local PDF, URL, arXiv ID, DOI, publisher page, or title")
    source.add_argument("--resume-workspace", help="Existing paper workspace to continue")
    parser.add_argument("--output-root", default=".")
    parser.add_argument("--workspace-name")
    parser.add_argument("--title")
    parser.add_argument("--authors")
    parser.add_argument("--year")
    parser.add_argument("--source-url")
    parser.add_argument("--mode", choices=VALID_MODES, default="deep_read")
    parser.add_argument("--paper-type", default="unclassified")
    parser.add_argument("--access-level", choices=VALID_ACCESS_LEVELS, default="unknown")
    parser.add_argument("--language", default="follow_user")
    parser.add_argument("--template")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument("--max-candidates", type=int, default=40)
    parser.add_argument("--keep-repeated-margins", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.max_candidates < 1:
        print("error: --max-candidates must be at least 1", file=sys.stderr)
        return 2
    try:
        result = run_pipeline(args)
    except (FileNotFoundError, FileExistsError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"].startswith("ready_for_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
