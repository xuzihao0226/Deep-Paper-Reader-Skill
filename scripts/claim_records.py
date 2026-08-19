#!/usr/bin/env python3
"""Prepare and validate human-reviewed claim-evidence records."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_DECISIONS = {"pending", "keep", "discard"}
VALID_CATEGORIES = {"explicit_author_claim", "source_backed_implication", "report_inference"}
VALID_SUPPORT = {"direct_and_decisive", "direct_but_limited", "indirect", "conflicted", "missing", "unavailable"}
VALID_VERDICTS = {
    "supported",
    "partially_supported",
    "not_established",
    "contradicted",
    "not_verifiable_from_available_source",
}
VALID_RESULT_BOUNDARIES = {"demonstrated", "planned", "assumed", "interpreted", "unavailable"}
REVIEWABLE_FIELDS = {
    "decision",
    "decision_reason",
    "authors_claim",
    "claim_category",
    "evidence_records",
    "support_strength",
    "largest_gap",
    "verdict",
    "safe_version",
    "wording_to_avoid",
    "result_claim_boundary",
    "review_notes",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def flatten_source_blocks(pages_payload: dict[str, Any]) -> list[dict[str, Any]]:
    blocks = []
    for page in pages_payload.get("pages", []):
        for block in page.get("blocks", []):
            if block.get("removed_as_repeated_margin"):
                continue
            blocks.append(
                {
                    "block_id": block["block_id"],
                    "pdf_page": page.get("pdf_page"),
                    "text": block.get("text", ""),
                    "heading_candidate": bool(block.get("heading_candidate")),
                }
            )
    return blocks


def context_for_locator(blocks: list[dict[str, Any]], locator: str) -> dict[str, Any]:
    index_by_id = {block["block_id"]: index for index, block in enumerate(blocks)}
    if locator not in index_by_id:
        return {"before": None, "target": None, "after": None}
    index = index_by_id[locator]
    return {
        "before": blocks[index - 1] if index > 0 else None,
        "target": blocks[index],
        "after": blocks[index + 1] if index + 1 < len(blocks) else None,
    }


def prepare_records(workspace: Path, force: bool = False) -> dict[str, Any]:
    candidates_path = workspace / "evidence" / "claim_candidates.json"
    pages_path = workspace / "evidence" / "pages.json"
    output_path = workspace / "evidence" / "claims.json"
    if not candidates_path.is_file():
        raise FileNotFoundError(f"claim_candidates.json not found; run analyze_structure.py first: {candidates_path}")
    if not pages_path.is_file():
        raise FileNotFoundError(f"pages.json not found: {pages_path}")
    if output_path.exists() and not force:
        raise FileExistsError(
            f"Refusing to overwrite claim review records: {output_path}. Use --force only after confirming replacement."
        )

    candidates = load_json(candidates_path).get("candidates", [])
    blocks = flatten_source_blocks(load_json(pages_path))
    records = []
    for index, candidate in enumerate(candidates, start=1):
        locator = candidate["source_locator"]
        records.append(
            {
                "claim_id": f"C{index}",
                "candidate_id": candidate.get("candidate_id"),
                "decision": "pending",
                "decision_reason": None,
                "review_status": "pending",
                "source_locator": locator,
                "pdf_page": candidate.get("pdf_page"),
                "section_id": candidate.get("section_id"),
                "section_type": candidate.get("section_type"),
                "candidate_text": candidate.get("text"),
                "source_context": context_for_locator(blocks, locator),
                "authors_claim": None,
                "claim_category": None,
                "evidence_records": [
                    {
                        "evidence_id": f"E{index}",
                        "source_locator": locator,
                        "source_type": "pdf_text_block",
                        "evidence_summary": None,
                        "relevance": None,
                        "limitation": None,
                    }
                ],
                "support_strength": None,
                "largest_gap": None,
                "verdict": None,
                "safe_version": None,
                "wording_to_avoid": None,
                "result_claim_boundary": None,
                "review_notes": None,
            }
        )
    payload = {
        "schema_version": 1,
        "created_at": utc_now(),
        "status": "pending_review",
        "instructions": (
            "Review source context before setting decision. Keep only central claims, complete all controlled fields, "
            "and validate before using records in report.md."
        ),
        "claims": records,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"workspace": str(workspace), "claim_record_count": len(records), "output": "evidence/claims.json"}


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def apply_review(workspace: Path, review_path: Path) -> dict[str, Any]:
    claims_path = workspace / "evidence" / "claims.json"
    pages_path = workspace / "evidence" / "pages.json"
    if not claims_path.is_file():
        raise FileNotFoundError(f"claims.json not found: {claims_path}")
    if not review_path.is_file():
        raise FileNotFoundError(f"review overlay not found: {review_path}")
    if not pages_path.is_file():
        raise FileNotFoundError(f"pages.json not found: {pages_path}")

    payload = load_json(claims_path)
    overlay = load_json(review_path)
    blocks = flatten_source_blocks(load_json(pages_path))
    valid_locators = {block["block_id"] for block in blocks}
    records = {claim.get("claim_id"): claim for claim in payload.get("claims", [])}
    review_items = overlay.get("claims", [])
    if not isinstance(review_items, list):
        raise ValueError("Review overlay field 'claims' must be a list.")

    reviewed_ids = set()
    for item in review_items:
        claim_id = item.get("claim_id")
        if claim_id not in records:
            raise ValueError(f"Review overlay refers to unknown claim_id: {claim_id!r}")
        if claim_id in reviewed_ids:
            raise ValueError(f"Review overlay repeats claim_id: {claim_id}")
        reviewed_ids.add(claim_id)
        decision = item.get("decision")
        if decision not in {"keep", "discard"}:
            raise ValueError(f"{claim_id}: overlay decision must be 'keep' or 'discard'.")
        record = records[claim_id]
        for key in REVIEWABLE_FIELDS:
            if key in item:
                record[key] = item[key]
        record["decision"] = decision
        record["review_status"] = "reviewed"

    new_items = overlay.get("new_claims", [])
    if not isinstance(new_items, list):
        raise ValueError("Review overlay field 'new_claims' must be a list.")
    for item in new_items:
        claim_id = item.get("claim_id")
        if not nonempty(claim_id) or claim_id in records or claim_id in reviewed_ids:
            raise ValueError(f"New review claim_id is missing or already exists: {claim_id!r}")
        locator = item.get("source_locator")
        if locator not in valid_locators:
            raise ValueError(f"{claim_id}: new claim source_locator does not exist: {locator!r}")
        decision = item.get("decision")
        if decision not in {"keep", "discard"}:
            raise ValueError(f"{claim_id}: new claim decision must be 'keep' or 'discard'.")
        target = next(block for block in blocks if block["block_id"] == locator)
        record = {
            "claim_id": claim_id,
            "candidate_id": None,
            "decision": decision,
            "decision_reason": None,
            "review_status": "reviewed",
            "source_locator": locator,
            "pdf_page": target.get("pdf_page"),
            "section_id": item.get("section_id"),
            "section_type": item.get("section_type"),
            "candidate_text": None,
            "source_context": context_for_locator(blocks, locator),
            "authors_claim": None,
            "claim_category": None,
            "evidence_records": [],
            "support_strength": None,
            "largest_gap": None,
            "verdict": None,
            "safe_version": None,
            "wording_to_avoid": None,
            "result_claim_boundary": None,
            "review_notes": None,
        }
        for key in REVIEWABLE_FIELDS:
            if key in item:
                record[key] = item[key]
        payload.setdefault("claims", []).append(record)
        records[claim_id] = record
        reviewed_ids.add(claim_id)

    if overlay.get("discard_unlisted"):
        reason = overlay.get("discard_reason")
        if not nonempty(reason):
            raise ValueError("discard_unlisted requires a non-empty discard_reason.")
        for claim_id, record in records.items():
            if claim_id not in reviewed_ids:
                record["decision"] = "discard"
                record["decision_reason"] = reason
                record["review_status"] = "reviewed"

    payload["status"] = "review_applied"
    payload["review_applied_at"] = utc_now()
    payload["review_source"] = str(review_path)
    claims_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "workspace": str(workspace),
        "reviewed_claim_count": len(reviewed_ids),
        "new_claim_count": len(new_items),
        "discarded_unlisted": bool(overlay.get("discard_unlisted")),
        "output": "evidence/claims.json",
    }


def validate_records(workspace: Path) -> dict[str, Any]:
    claims_path = workspace / "evidence" / "claims.json"
    pages_path = workspace / "evidence" / "pages.json"
    if not claims_path.is_file():
        raise FileNotFoundError(f"claims.json not found: {claims_path}")
    if not pages_path.is_file():
        raise FileNotFoundError(f"pages.json not found: {pages_path}")

    payload = load_json(claims_path)
    claims = payload.get("claims", [])
    valid_locators = {
        block["block_id"]
        for page in load_json(pages_path).get("pages", [])
        for block in page.get("blocks", [])
    }
    errors = []
    warnings = []
    claim_ids = [str(claim.get("claim_id", "")) for claim in claims]
    if len(claim_ids) != len(set(claim_ids)):
        errors.append("Claim IDs must be unique.")

    kept = []
    all_evidence_ids = []
    for claim in claims:
        claim_id = claim.get("claim_id") or "<missing claim id>"
        decision = claim.get("decision")
        if decision not in VALID_DECISIONS:
            errors.append(f"{claim_id}: invalid decision {decision!r}.")
            continue
        if decision == "pending":
            errors.append(f"{claim_id}: decision is still pending.")
            continue
        if decision == "discard":
            if not nonempty(claim.get("decision_reason")):
                errors.append(f"{claim_id}: discarded records require decision_reason.")
            continue

        kept.append(claim)
        required_text_fields = (
            "authors_claim",
            "largest_gap",
            "safe_version",
            "wording_to_avoid",
            "review_notes",
        )
        if claim.get("review_status") != "reviewed":
            errors.append(f"{claim_id}: review_status must be 'reviewed'.")
        for field in required_text_fields:
            if not nonempty(claim.get(field)):
                errors.append(f"{claim_id}: missing {field}.")
        if claim.get("claim_category") not in VALID_CATEGORIES:
            errors.append(f"{claim_id}: invalid claim_category.")
        if claim.get("support_strength") not in VALID_SUPPORT:
            errors.append(f"{claim_id}: invalid support_strength.")
        if claim.get("verdict") not in VALID_VERDICTS:
            errors.append(f"{claim_id}: invalid verdict.")
        if claim.get("result_claim_boundary") not in VALID_RESULT_BOUNDARIES:
            errors.append(f"{claim_id}: invalid result_claim_boundary.")
        if claim.get("source_locator") not in valid_locators:
            errors.append(f"{claim_id}: source_locator does not exist in pages.json.")

        evidence_records = claim.get("evidence_records") or []
        if not evidence_records:
            errors.append(f"{claim_id}: at least one evidence record is required.")
        for evidence in evidence_records:
            evidence_id = evidence.get("evidence_id")
            if not nonempty(evidence_id):
                errors.append(f"{claim_id}: evidence record is missing evidence_id.")
            else:
                all_evidence_ids.append(evidence_id)
            if evidence.get("source_locator") not in valid_locators:
                errors.append(f"{claim_id}/{evidence_id}: evidence source_locator does not exist in pages.json.")
            for field in ("source_type", "evidence_summary", "relevance", "limitation"):
                if not nonempty(evidence.get(field)):
                    errors.append(f"{claim_id}/{evidence_id}: missing {field}.")

    if not kept:
        errors.append("At least one reviewed claim must be kept for a final full-text report.")
    if len(all_evidence_ids) != len(set(all_evidence_ids)):
        errors.append("Evidence IDs must be unique across kept claims.")
    if len(kept) > 12:
        warnings.append("More than 12 claims were kept; confirm that all are central rather than supporting details.")

    result = {
        "schema_version": 1,
        "validated_at": utc_now(),
        "passed": not errors,
        "kept_claim_count": len(kept),
        "discarded_claim_count": sum(1 for claim in claims if claim.get("decision") == "discard"),
        "pending_claim_count": sum(1 for claim in claims if claim.get("decision") == "pending"),
        "errors": errors,
        "warnings": warnings,
    }
    (workspace / "evidence" / "claim-validation.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare", help="Create review records from claim candidates")
    prepare.add_argument("--workspace", required=True)
    prepare.add_argument("--force", action="store_true")
    validate = subparsers.add_parser("validate", help="Validate reviewed claim records")
    validate.add_argument("--workspace", required=True)
    apply_review_parser = subparsers.add_parser("apply-review", help="Merge a compact human-review overlay")
    apply_review_parser.add_argument("--workspace", required=True)
    apply_review_parser.add_argument("--review", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    workspace = Path(args.workspace).expanduser().resolve()
    try:
        if args.command == "prepare":
            result = prepare_records(workspace, args.force)
            exit_code = 0
        elif args.command == "apply-review":
            result = apply_review(workspace, Path(args.review).expanduser().resolve())
            exit_code = 0
        else:
            result = validate_records(workspace)
            exit_code = 0 if result["passed"] else 1
    except (FileNotFoundError, FileExistsError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
