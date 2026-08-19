#!/usr/bin/env python3
"""Validate a Deep Paper Reader report before delivery.

Duplicate-paragraph, Markdown image, encoding, and math checks are directly
adapted from sodalone/paper-reading-skill's validate_report.py and
validate_report_text.py with the project owner's permission. Fixed arXiv-only
contracts are replaced by cross-disciplinary bilingual checks.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
FENCED_CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
DISPLAY_MATH_RE = re.compile(r"\$\$(.+?)\$\$|\\\[(.+?)\\\]", re.DOTALL)
INLINE_MATH_RE = re.compile(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", re.DOTALL)
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
PLACEHOLDER_RE = re.compile(r"\{\{[^{}]+\}\}|\bTBD\b|\bTODO\b|To be resolved|待补充|待确认", re.I)
CLAIM_ID_RE = re.compile(r"\bC\d+\b", re.I)
TABLE_CLAIM_ROW_RE = re.compile(r"(?m)^\|\s*(C\d+)\s*\|(.+)\|\s*$", re.I)
SOURCE_LOCATOR_RE = re.compile(
    r"P\d{3}-B\d{3}|\b(?:p(?:age)?\.?|pp\.?)\s*\d+|"
    r"\b(?:sec(?:tion)?\.?|chapter)\s*\d+(?:\.\d+)*|\bappendix\s*[A-Z\d]+|"
    r"\b(?:figure|fig\.?|table|equation|eq\.?|theorem|lemma|proposition)\s*[\w.\-]+|"
    r"(?:第\s*\d+\s*页|第[一二三四五六七八九十\d]+[章节]|图\s*\d+|表\s*\d+|附录\s*[A-Za-z一二三四五六七八九十\d]*)",
    re.I,
)

SUSPICIOUS_TOKENS = ["璁烘枃", "闃呰", "鍩烘湰", "闄勫綍", "寰呰ˉ", "鏈枃", "鏂囩尞", "锛"]

MATH_COMPAT_RULES = [
    (
        re.compile(r"\\mathbbm\b"),
        "Found `\\mathbbm`, which common Markdown math renderers may not support; use a compatible indicator notation.",
    ),
    (
        re.compile(r"\\tag\s*\{"),
        "Found `\\tag{}`; keep equation numbering in prose rather than inside the math block.",
    ),
]

REQUIRED_HEADING_GROUPS = {
    "three_minute_understanding": ("three-minute understanding", "three minute understanding", "三分钟理解", "三分钟读懂"),
    "identity_and_access": ("paper identity", "identity and access", "论文身份", "论文信息", "访问边界"),
    "research_question": ("research question", "research thesis", "研究问题", "核心问题", "中心论题", "论题"),
    "concepts": ("essential concepts", "key concepts", "核心概念", "必要概念", "术语"),
    "method_or_argument": ("method, theory, or argument", "method or argument", "方法、理论或论证", "方法与论证", "论证结构"),
    "claims_and_evidence": ("claims and evidence", "claim-evidence", "论点与证据", "主张与证据", "证据是否成立"),
    "contributions": ("contributions", "genuine novelty", "贡献", "创新"),
    "limitations": ("limitations", "objections", "open questions", "局限", "异议", "开放问题"),
    "final_judgment": ("final judgment", "next actions", "最终判断", "后续行动", "阅读建议"),
    "evidence_index": ("evidence index", "evidence location", "证据索引", "证据定位"),
    "report_boundary": ("report boundary", "报告边界", "使用边界"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_paragraph(paragraph: str) -> str:
    return re.sub(r"\s+", " ", paragraph).strip()


def clean_text(text: str) -> str:
    return HTML_COMMENT_RE.sub("", text).strip()


def duplicate_long_paragraphs(text: str) -> list[str]:
    cleaned = HTML_COMMENT_RE.sub("", text)
    paragraphs = []
    for raw in re.split(r"\n\s*\n", cleaned):
        paragraph = normalize_paragraph(raw)
        if len(paragraph) < 100:
            continue
        if paragraph.startswith(("#", "|", "!", "$$")):
            continue
        paragraphs.append(paragraph)
    counts = Counter(paragraphs)
    return [paragraph for paragraph, count in counts.items() if count > 1]


def count_private_use_chars(text: str) -> int:
    return sum(1 for char in text if 0xE000 <= ord(char) <= 0xF8FF)


def strip_non_report_markup(text: str) -> str:
    return FENCED_CODE_BLOCK_RE.sub("", HTML_COMMENT_RE.sub("", text))


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def scan_math_segment(segment: str, base_line: int) -> list[str]:
    issues = []
    for pattern, message in MATH_COMPAT_RULES:
        match = pattern.search(segment)
        if match:
            issues.append(f"line {base_line + segment[:match.start()].count(chr(10))}: {message}")
    lines = segment.splitlines()
    has_aligned_env = "\\begin{aligned}" in segment or "\\begin{array}" in segment
    if len(lines) > 1 and not has_aligned_env:
        for index, line in enumerate(lines[1:], start=1):
            if re.match(r"^\s*[+\-*]", line):
                issues.append(
                    f"line {base_line + index}: Found a bare multiline display continuation; use one line or an aligned environment."
                )
                break
    return issues


def collect_math_issues(text: str) -> list[str]:
    cleaned = strip_non_report_markup(text)
    issues = []
    for match in DISPLAY_MATH_RE.finditer(cleaned):
        segment = match.group(1) if match.group(1) is not None else match.group(2)
        issues.extend(scan_math_segment(segment, line_number(cleaned, match.start())))
    inline_source = DISPLAY_MATH_RE.sub("", cleaned)
    for match in INLINE_MATH_RE.finditer(inline_source):
        issues.extend(scan_math_segment(match.group(1), line_number(inline_source, match.start())))
    return list(dict.fromkeys(issues))


def normalized_headings(text: str) -> list[str]:
    headings = re.findall(r"(?m)^#{2,4}\s+(.+?)\s*$", text)
    return [re.sub(r"\s+", " ", heading).strip().lower() for heading in headings]


def missing_heading_groups(text: str) -> list[str]:
    headings = normalized_headings(text)
    missing = []
    for group, variants in REQUIRED_HEADING_GROUPS.items():
        if not any(any(variant.lower() in heading for variant in variants) for heading in headings):
            missing.append(group)
    return missing


def extract_heading_section(text: str, variants: tuple[str, ...]) -> str:
    heading_pattern = re.compile(r"(?mi)^(#{2,4})\s+(.+)$")
    matches = list(heading_pattern.finditer(text))
    for index, match in enumerate(matches):
        title = match.group(2).strip().lower()
        if not any(variant.lower() in title for variant in variants):
            continue
        level = len(match.group(1))
        end = len(text)
        for later in matches[index + 1 :]:
            if len(later.group(1)) <= level:
                end = later.start()
                break
        return text[match.end() : end].strip()
    return ""


def claim_rows(text: str) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for match in TABLE_CLAIM_ROW_RE.finditer(text):
        rows.setdefault(match.group(1).upper(), []).append(match.group(2))
    return rows


def broken_image_paths(text: str, workspace: Path) -> list[str]:
    broken = []
    for raw_path in IMAGE_RE.findall(text):
        path_value = raw_path.strip().split(maxsplit=1)[0].strip("<>")
        if re.match(r"^(?:https?://|data:)", path_value, re.I):
            continue
        if not (workspace / path_value).resolve().is_file():
            broken.append(path_value)
    return sorted(set(broken))


def validate_report(
    text: str, workspace: Path, metadata: dict[str, Any] | None = None, final: bool = False
) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []
    metadata = metadata or {}
    cleaned = clean_text(text)
    headings = normalized_headings(text)
    placeholders = PLACEHOLDER_RE.findall(text)
    math_issues = collect_math_issues(text)
    private_count = count_private_use_chars(text)
    replacement_count = text.count("\ufffd")
    suspicious_counts = {token: text.count(token) for token in SUSPICIOUS_TOKENS if token in text}
    duplicates = duplicate_long_paragraphs(text)
    broken_images = broken_image_paths(text, workspace)
    claims = claim_rows(text)
    locator_count = len(SOURCE_LOCATOR_RE.findall(text))

    metrics: dict[str, Any] = {
        "total_characters": len(cleaned),
        "heading_count": len(headings),
        "claim_count": len(claims),
        "source_locator_count": locator_count,
        "image_count": len(IMAGE_RE.findall(text)),
        "broken_image_count": len(broken_images),
        "placeholder_count": len(placeholders),
        "duplicate_long_paragraph_count": len(duplicates),
        "private_use_character_count": private_count,
        "replacement_character_count": replacement_count,
        "math_issue_count": len(math_issues),
    }

    if private_count:
        errors.append(f"Private-use glyphs detected: {private_count}.")
    if replacement_count:
        errors.append(f"Unicode replacement characters detected: {replacement_count}.")
    if sum(suspicious_counts.values()) >= 3:
        errors.append(f"Possible mojibake tokens detected: {suspicious_counts}.")
    errors.extend(f"Math compatibility issue: {issue}" for issue in math_issues)
    if broken_images:
        errors.append("Broken local image paths: " + ", ".join(broken_images))

    if final:
        missing = missing_heading_groups(text)
        if missing:
            errors.append("Missing required report sections: " + ", ".join(missing))
        if HTML_COMMENT_RE.search(text):
            errors.append("Final report still contains HTML comments.")
        if placeholders:
            errors.append("Final report still contains placeholders: " + ", ".join(sorted(set(placeholders))))
        if not claims:
            errors.append("Final report contains no completed C-numbered claim rows.")
        for claim_id, rows in claims.items():
            if not any(SOURCE_LOCATOR_RE.search(row) for row in rows):
                errors.append(f"{claim_id} has no stable source locator in its report rows.")
        if locator_count == 0:
            errors.append("Final report contains no stable source locators.")
        if duplicates:
            errors.append(f"Found {len(duplicates)} duplicated paragraphs of at least 100 characters.")

        summary = extract_heading_section(text, REQUIRED_HEADING_GROUPS["three_minute_understanding"])
        if len(clean_text(summary)) < 150:
            errors.append("Three-minute understanding section is too short to cover the question, idea, conclusion, and evidence.")

        access_level = metadata.get("reading", {}).get("access_level")
        if access_level == "abstract_only" and not re.search(
            r"abstract[_ -]?only|only the abstract|仅摘要|只有摘要|摘要可用", text, re.I
        ):
            errors.append("Metadata says abstract_only, but the report does not disclose that access boundary.")
        if access_level in {"partial_text", "unknown"} and not re.search(
            r"partial[_ -]?text|部分正文|访问限制|无法核验|not verifiable|unavailable", text, re.I
        ):
            warnings.append("The report may not clearly disclose its partial or unknown source-access boundary.")

    if metrics["total_characters"] < 1500:
        warnings.append("The report is short; confirm that no central argument, claim, or decisive evidence was omitted.")
    if metrics["heading_count"] > 40:
        warnings.append("The report has more than 40 headings and may be overly fragmented.")

    return errors, warnings, metrics


def validate_workspace(workspace: Path, final: bool = False) -> dict[str, Any]:
    report_path = workspace / "report.md"
    metadata_path = workspace / "metadata.json"
    if not report_path.is_file():
        raise FileNotFoundError(f"report.md not found: {report_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
    text = report_path.read_text(encoding="utf-8-sig")
    errors, warnings, metrics = validate_report(text, workspace, metadata, final)
    payload = {
        "schema_version": 1,
        "validated_at": utc_now(),
        "stage": "final" if final else "draft",
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }
    evidence_dir = workspace / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "validation.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--final", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = validate_workspace(Path(args.workspace).expanduser().resolve(), args.final)
    except (FileNotFoundError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
