#!/usr/bin/env python3
"""Reconstruct paper sections and surface traceable claim candidates."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SECTION_RULES = [
    ("abstract", ("abstract", "摘要", "概要")),
    ("introduction", ("introduction", "background", "引言", "绪论", "研究背景")),
    ("related_work", ("related work", "literature review", "相关工作", "文献综述", "研究现状")),
    ("method", ("method", "methodology", "approach", "model", "方法", "方法论", "研究设计", "模型")),
    ("experiment", ("experiment", "experimental setup", "evaluation", "实验", "评估", "评价")),
    ("results", ("results", "findings", "结果", "研究发现")),
    ("discussion", ("discussion", "analysis", "讨论", "分析")),
    ("argument", ("argument", "proof", "demonstration", "论证", "证明", "推论")),
    ("objection_response", ("objection", "reply", "response", "异议", "反驳", "回应", "答辩")),
    ("limitations", ("limitation", "threats to validity", "局限", "限制", "效度威胁")),
    ("conclusion", ("conclusion", "concluding", "结论", "结语", "总结")),
    ("references", ("references", "bibliography", "notes", "参考文献", "文献目录", "注释")),
    ("appendix", ("appendix", "supplement", "附录", "补充材料")),
]

CLAIM_CUES = {
    "author_claim": (
        r"\bwe (?:argue|claim|propose|contend|show|demonstrate)\b",
        r"\bi (?:argue|claim|propose|contend|maintain|conclude|suggest|show|demonstrate)\b",
        r"\bmy (?:argument|claim|position|conclusion)\b",
        r"\bit is (?:argued|claimed|proposed|contended|maintained|concluded|suggested|shown|demonstrated) that\b",
        r"\bthe authors? (?:argue|claim|propose|contend|show|demonstrate)s?\b",
        r"本文(?:认为|主张|提出|表明|论证)",
        r"作者(?:认为|主张|提出|表明|论证)",
        r"我们(?:认为|主张|提出|表明|论证)",
    ),
    "result": (
        r"\b(?:results?|findings?|evidence) (?:show|shows|indicate|indicates|suggest|suggests|demonstrate|demonstrates)\b",
        r"\bwe (?:find|found|observe|observed|outperform|outperformed)\b",
        r"结果(?:表明|显示|说明)",
        r"研究发现",
        r"证据(?:表明|显示|支持)",
    ),
    "inference": (
        r"\b(?:therefore|thus|hence|consequently|it follows that)\b",
        r"(?:因此|所以|由此|因而|进而|这意味着)",
    ),
    "normative": (
        r"\b(?:should|ought to|must|need to|needs to)\b",
        r"(?:应当|应该|必须|需要|有必要)",
    ),
    "contribution": (
        r"\b(?:our|the) (?:main |key )?contribution(?:s)?\b",
        r"\bwe introduce\b",
        r"(?:主要|核心|本文的)?贡献(?:在于|包括|是)",
        r"本文首次",
    ),
    "scope": (
        r"^in this (?:manuscript|paper|chapter|section),? we (?:cover|discuss|focus on|provide|present|review|survey|summarize|give an overview|give a brief introduction)\b",
        r"\bwe (?:cover|focus on|do not discuss|only briefly discuss|give an overview|give a brief introduction|provide an overview)\b",
        r"\bthis (?:manuscript|paper|chapter|section) (?:covers|discusses|focuses on|provides|presents|reviews|surveys|summarizes)\b",
        r"本文(?:覆盖|讨论|重点介绍|综述|回顾|不讨论)",
    ),
    "limitation": (
        r"\b(?:limitation|limitations|cannot|does not|do not|future work)\b",
        r"(?:局限|限制|尚不能|无法|未来研究|有待)",
    ),
    "objection": (
        r"\b(?:objection|counterargument|however|nevertheless|one might argue)\b",
        r"(?:异议|反对意见|然而|但是|可能有人认为|反驳)",
    ),
}

CLAIM_WEIGHTS = {
    "author_claim": 5,
    "result": 4,
    "contribution": 4,
    "scope": 5,
    "inference": 2,
    "limitation": 2,
    "objection": 2,
    "normative": 1,
}

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。！？；;])\s+")
NUMBERING_RE = re.compile(r"^\s*(?:\d+(?:\.\d+)*|[IVXLC]+|[一二三四五六七八九十]+)[.)、]?\s*")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_heading(title: str) -> str:
    value = NUMBERING_RE.sub("", title.replace("\n", " ")).strip().lower()
    return re.sub(r"\s+", " ", value)


def classify_section(title: str) -> str:
    normalized = normalize_heading(title)
    for section_type, keywords in SECTION_RULES:
        if any(keyword in normalized for keyword in keywords):
            return section_type
    if NUMBERING_RE.match(title):
        return "numbered_section"
    return "other"


def flatten_blocks(pages_payload: dict[str, Any]) -> list[dict[str, Any]]:
    blocks = []
    for page in pages_payload.get("pages", []):
        for block in page.get("blocks", []):
            if block.get("removed_as_repeated_margin"):
                continue
            item = dict(block)
            item["pdf_page"] = page.get("pdf_page")
            blocks.append(item)
    return blocks


def build_sections(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    def start_section(title: str, section_type: str, heading_locator: str | None) -> dict[str, Any]:
        return {
            "section_id": f"S{len(sections) + 1:03d}",
            "title": title,
            "section_type": section_type,
            "heading_locator": heading_locator,
            "block_ids": [],
            "pages": [],
            "character_count": 0,
        }

    for block in blocks:
        if block.get("heading_candidate"):
            if current is not None:
                sections.append(current)
            current = start_section(block["text"].replace("\n", " "), classify_section(block["text"]), block["block_id"])
            continue
        if current is None:
            current = start_section("Front matter or unsectioned opening", "front_matter", None)
        current["block_ids"].append(block["block_id"])
        page = block.get("pdf_page")
        if page not in current["pages"]:
            current["pages"].append(page)
        current["character_count"] += len(block.get("text", ""))

    if current is not None:
        sections.append(current)
    if not sections and blocks:
        fallback = start_section("Document body", "document_body", None)
        for block in blocks:
            fallback["block_ids"].append(block["block_id"])
            if block.get("pdf_page") not in fallback["pages"]:
                fallback["pages"].append(block.get("pdf_page"))
            fallback["character_count"] += len(block.get("text", ""))
        sections.append(fallback)
    for section in sections:
        section["start_locator"] = section["heading_locator"] or (section["block_ids"][0] if section["block_ids"] else None)
        section["end_locator"] = section["block_ids"][-1] if section["block_ids"] else section["heading_locator"]
    return sections


def section_lookup(sections: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup = {}
    for section in sections:
        if section.get("heading_locator"):
            lookup[section["heading_locator"]] = section
        for block_id in section["block_ids"]:
            lookup[block_id] = section
    return lookup


def cue_matches(text: str) -> tuple[list[str], list[str]]:
    categories = []
    matches = []
    for category, patterns in CLAIM_CUES.items():
        category_matches = []
        for pattern in patterns:
            found = re.findall(pattern, text, flags=re.I)
            category_matches.extend(str(item) for item in found)
        if category_matches:
            categories.append(category)
            matches.extend(category_matches)
    return categories, sorted(set(matches), key=str.lower)


def build_claim_candidates(
    blocks: list[dict[str, Any]], sections: list[dict[str, Any]], max_candidates: int, review_like: bool = False
) -> list[dict[str, Any]]:
    lookup = section_lookup(sections)
    candidates = []
    seen = set()
    for block in blocks:
        if block.get("heading_candidate"):
            continue
        section = lookup.get(block["block_id"], {})
        if section.get("section_type") in {"front_matter", "references"}:
            continue
        sentences = [part.strip() for part in SENTENCE_SPLIT_RE.split(block.get("text", "")) if part.strip()]
        if not sentences:
            sentences = [block.get("text", "").strip()]
        for sentence in sentences:
            if len(sentence) < 12 or len(sentence) > 1200:
                continue
            categories, matches = cue_matches(sentence)
            if not categories:
                continue
            if review_like and re.search(r"\b(?:figure|fig\.|table)\b", sentence, re.I) and re.search(
                r"\bwe show\b", sentence, re.I
            ):
                continue
            dedupe_key = re.sub(r"\W+", "", sentence.lower())
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            score = sum(CLAIM_WEIGHTS.get(category, 0) for category in categories)
            if section.get("section_type") == "conclusion":
                score += 3
            elif section.get("section_type") in {"abstract", "introduction"}:
                score += 2
            candidates.append(
                {
                    "candidate_id": "",
                    "source_locator": block["block_id"],
                    "pdf_page": block.get("pdf_page"),
                    "section_id": section.get("section_id"),
                    "section_type": section.get("section_type"),
                    "cue_categories": categories,
                    "matched_cues": matches,
                    "retrieval_score": score,
                    "text": sentence,
                    "review_status": "unreviewed_candidate_not_a_verified_claim",
                }
            )
    candidates = sorted(
        sorted(enumerate(candidates), key=lambda item: (-item[1]["retrieval_score"], item[0]))[:max_candidates],
        key=lambda item: item[0],
    )
    candidates = [candidate for _, candidate in candidates]
    for index, candidate in enumerate(candidates, start=1):
        candidate["candidate_id"] = f"CC{index:03d}"
    return candidates


def markdown_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def build_reading_map(sections: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> str:
    lines = [
        "# Reading Map",
        "",
        "> Section types and claim candidates are heuristic navigation aids, not final scholarly judgments.",
        "",
        "## Section Outline",
        "",
        "| Section | Detected type | Pages | Locator range | Characters |",
        "|---|---|---|---|---:|",
    ]
    for section in sections:
        pages = ", ".join(str(page) for page in section["pages"]) or "—"
        locator_range = f"{section['start_locator'] or '—'} → {section['end_locator'] or '—'}"
        lines.append(
            f"| {markdown_escape(section['title'])} | `{section['section_type']}` | {pages} | "
            f"{locator_range} | {section['character_count']} |"
        )
    lines.extend(
        [
            "",
            "## Claim Candidates Requiring Review",
            "",
            "| Candidate | Source | Section | Signal | Text |",
            "|---|---|---|---|---|",
        ]
    )
    for candidate in candidates:
        text = candidate["text"]
        if len(text) > 240:
            text = text[:237].rstrip() + "..."
        lines.append(
            f"| {candidate['candidate_id']} | {candidate['source_locator']} | "
            f"{candidate.get('section_type') or '—'} | {', '.join(candidate['cue_categories'])} | "
            f"{markdown_escape(text)} |"
        )
    if not candidates:
        lines.append("| — | — | — | — | No cue-based candidates found; review the section outline manually. |")
    return "\n".join(lines).rstrip() + "\n"


def update_metadata(workspace: Path, summary: dict[str, Any]) -> None:
    metadata_path = workspace / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    extraction = metadata.setdefault("extraction", {})
    extraction.update(
        {
            "structure_status": "reading_map_ready",
            "sections_json": "evidence/sections.json",
            "claim_candidates_json": "evidence/claim_candidates.json",
            "reading_map": "evidence/reading-map.md",
            "section_count": summary["section_count"],
            "claim_candidate_count": summary["claim_candidate_count"],
        }
    )
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def analyze_workspace(workspace: Path, max_candidates: int = 40) -> dict[str, Any]:
    pages_path = workspace / "evidence" / "pages.json"
    metadata_path = workspace / "metadata.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"metadata.json not found: {metadata_path}")
    if not pages_path.is_file():
        raise FileNotFoundError(f"pages.json not found; run extract_text.py first: {pages_path}")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    paper = metadata.get("paper", {})
    review_signal = " ".join(
        str(value) for value in (paper.get("title", ""), paper.get("abstract", "")) if value
    ).lower()
    review_like = any(term in review_signal for term in ("overview", "review", "survey", "tutorial"))
    payload = json.loads(pages_path.read_text(encoding="utf-8"))
    blocks = flatten_blocks(payload)
    sections = build_sections(blocks)
    candidates = build_claim_candidates(blocks, sections, max_candidates, review_like=review_like)
    evidence_dir = workspace / "evidence"

    sections_payload = {"schema_version": 1, "generated_at": utc_now(), "sections": sections}
    candidates_payload = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "warning": "Candidates are navigation aids and must be reviewed before becoming claim records.",
        "candidates": candidates,
    }
    (evidence_dir / "sections.json").write_text(
        json.dumps(sections_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (evidence_dir / "claim_candidates.json").write_text(
        json.dumps(candidates_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (evidence_dir / "reading-map.md").write_text(build_reading_map(sections, candidates), encoding="utf-8")
    summary = {
        "workspace": str(workspace),
        "section_count": len(sections),
        "claim_candidate_count": len(candidates),
        "unclassified_section_count": sum(1 for section in sections if section["section_type"] == "other"),
        "candidate_strategy": "review_scope" if review_like else "general_claim",
    }
    update_metadata(workspace, summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--max-candidates", type=int, default=40)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.max_candidates < 1:
        print("error: --max-candidates must be at least 1", file=sys.stderr)
        return 2
    try:
        summary = analyze_workspace(Path(args.workspace).expanduser().resolve(), args.max_candidates)
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
