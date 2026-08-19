---
name: deep-paper-reader
description: Read, explain, and critically review one academic paper with traceable evidence. Use when a user provides a local PDF, direct PDF URL, arXiv link or ID, DOI, or identifiable paper title and asks for a quick read, deep read, structured explanation, critical review, claim verification, method or argument analysis, or a reusable Markdown reading report. Support experimental, technical, theoretical, mathematical, systems, dataset, review, humanities, philosophy, and social-science papers. Do not use for multi-paper literature reviews, unsupported paper writing, or analysis without access to at least the abstract; never imply full-text review when only metadata or an abstract is available.
---

# Deep Paper Reader

## Overview

Turn one academic paper into an understandable, evidence-grounded, reusable reading report. Match the reading method to the paper type, distinguish the authors' claims from the report's inferences, and preserve source locations for every conclusion that could change the reader's judgment.

## Executable Quick Start

For a new paper, run deterministic preprocessing through the claim-review gate:

```bash
python3 "<skill-root>/scripts/run_pipeline.py" \
  --paper "<local PDF, URL, arXiv ID, DOI, publisher page, or title>" \
  --output-root "<user-selected output root>" \
  --mode "<quick_read|deep_read|critical_review>"
```

Use `--resume-workspace "<paper workspace>"` to continue an interrupted run without replacing existing claim-review records. Read `evidence/pipeline.json` for stage status. The deterministic pipeline stops at `ready_for_claim_review`; it does not make final scholarly judgments or write a completed report automatically.

## Core Rules

- Help the user understand before evaluating. Explain the problem, concepts, structure, method, or argument before presenting criticism.
- Treat evidence traceability as mandatory. Locate consequential claims by page, section, paragraph, figure, table, theorem, appendix, or another stable source marker.
- Match the evaluation standard to the paper type. Do not demand experiments from a philosophical argument or mathematical proof, and do not accept rhetoric as evidence for an empirical claim.
- Keep the researcher in control. Ask only when a missing choice would materially change the report; otherwise infer a sensible default and state it briefly.
- Separate author claims, source-backed implications, and report inferences. Never present one category as another.
- State uncertainty directly. Use formulations such as "the paper does not report this," "only the abstract was available," or "the current source does not support this conclusion."
- Produce one primary Markdown report rather than scattering the analysis across multiple parallel files.

## Workflow

### 1. Resolve the Paper Input

Classify the input before reading:

| Input | Action |
|---|---|
| Local PDF | Read the supplied file and preserve its original filename in metadata. |
| Direct PDF URL | Download the PDF, record the resolved URL, and verify that the response is a readable PDF. |
| arXiv link or ID | Resolve the paper metadata and obtain the corresponding PDF. |
| DOI or publisher page | Resolve bibliographic metadata, then obtain an openly accessible full text when available. |
| Paper title only | Search for an authoritative record and accessible full text; confirm identity if multiple papers match. |

Record the access level as one of:

- `full_text`: the complete paper is readable;
- `partial_text`: only some sections or a manuscript fragment are readable;
- `abstract_only`: only metadata and abstract are available.

Never produce a full-text review from `abstract_only`. In that case, provide an explicitly labeled abstract-based briefing and list what cannot be verified.

After preparing the workspace, run the bundled source resolver:

```bash
python3 "<skill-root>/scripts/fetch_source.py" \
  --workspace "<paper workspace>"
```

Use its recorded acquisition status and verified PDF signature rather than assuming that a successful HTTP response is a paper. Treat `full_text_ready` as source availability, then verify extraction separately. Treat `abstract_only`, `metadata_only`, `needs_authoritative_search`, and `failed` as explicit limits. For a title-only input, use authoritative scholarly search to identify candidate records and ask for confirmation when more than one plausible paper matches; then prepare or update the workspace with the resolved DOI, arXiv ID, or source URL.

For image-only or badly encoded PDFs, attempt text extraction or optical character recognition only when available. Report extraction limitations instead of guessing missing passages.

### 2. Determine the Reading Mode

Use the user's explicit request when present. Otherwise default to `deep_read`.

- `quick_read`: Help the user decide whether and where to read. Cover the research problem, central idea, approach or argument, main conclusion, decisive evidence, and reading value.
- `deep_read`: Build a systematic understanding of the entire paper. Cover concepts, structure, method or argument, evidence, contributions, limitations, and source locations.
- `critical_review`: Test whether the central claims are adequately supported. Emphasize assumptions, controls, proof gaps, alternative explanations, implementation semantics, external validity, and the strength of each verdict.

Ask the user to choose a mode only when the request is genuinely ambiguous and the difference would materially alter time, depth, or output. Do not interrupt a clear request with routine questions.

### 3. Infer Reader Context and Output Language

Follow the language of the user's request unless they specify otherwise. Match explanations to the reader's stated background. If no background is given, assume an educated reader who knows the broad field but not the paper's subtopic.

On first use of an abbreviation, provide:

1. the full English term;
2. a translation or plain-language meaning in the report language;
3. one sentence explaining what it does in this paper.

Do not overload the report with definitions that are not needed to follow the main line of reasoning.

### 4. Classify the Paper

Choose one primary type and any necessary secondary type:

- experimental or observational study;
- technical or method paper;
- theoretical or mathematical paper;
- system, platform, benchmark, or dataset paper;
- literature review, systematic review, or meta-analysis;
- philosophy or humanities argument paper;
- social-science empirical or conceptual paper.

Use the classification to choose evidence and criticism. Hybrid papers may require more than one route, but do not mechanically fill every route.

Read `references/paper-types.md` after the initial classification and apply only the primary and necessary secondary review routes.

### 5. Prepare a Durable Workspace

Create or reuse one paper workspace under the user-selected output root:

```text
{paper_slug}/
├── report.md
├── metadata.json
├── source/
├── images/
└── evidence/
```

- `report.md`: the only primary reading report;
- `metadata.json`: title, authors, year, identifiers, source URLs, access level, reading mode, paper type, and extraction status;
- `source/`: the original PDF and any authoritative source material;
- `images/`: only figures or tables used in the report;
- `evidence/`: structured claim and source-location records used to verify the report.

For a new paper, initialize this structure with the bundled script:

```bash
python3 "<skill-root>/scripts/prepare_workspace.py" \
  --paper "<local PDF, URL, arXiv ID, DOI, or title>" \
  --output-root "<user-selected output root>" \
  --mode "<quick_read|deep_read|critical_review>"
```

Add `--title`, `--authors`, `--year`, `--source-url`, `--paper-type`, `--access-level`, and `--language` only when those values are known. The script copies a local PDF to `source/paper.pdf`, records normalized input metadata, and creates the initial report from `assets/report-template.md`.

Run `scripts/fetch_source.py` next. It updates `metadata.json`, preserves authoritative source records under `source/`, and writes a verified accessible PDF to `source/paper.pdf` when available. Do not treat Crossref metadata, a publisher landing page, or an HTML paywall response as full text.

When `source/paper.pdf` exists, extract traceable text before reading:

```bash
python3 "<skill-root>/scripts/extract_text.py" \
  --workspace "<paper workspace>"
```

Use `evidence/fulltext.md` for readable text, `evidence/pages.json` for page and block geometry, and `evidence/extraction.json` for quality limits. Stable text locators use `P###-B###`; combine them with the PDF page number in consequential evidence citations. Treat `needs_ocr` or `partial_text_ready` as an access limitation. Do not infer that the complete paper was read merely because the PDF file exists.

Build a navigation map after text extraction:

```bash
python3 "<skill-root>/scripts/analyze_structure.py" \
  --workspace "<paper workspace>"
```

Read `evidence/reading-map.md` to navigate the detected outline, `evidence/sections.json` for section ranges, and `evidence/claim_candidates.json` for cue-based sentences. Treat section types as heuristic labels and every claim candidate as unreviewed. Verify each candidate against its surrounding blocks in `evidence/pages.json` before promoting it to a formal claim record. Add central claims the cue rules missed; discard rhetorical, background, citation, or negated sentences that are not the focal authors' claims.

For an arXiv paper with `source/arxiv-source.tar`, extract author-supplied figures and their LaTeX context with the reused source-first extractor:

```bash
python3 "<skill-root>/scripts/extract_figures.py" \
  --workspace "<paper workspace>"
```

Read `evidence/images_manifest.json` before choosing figures for the report. Prefer figures recovered from the author's source bundle over webpage screenshots. Include only figures that improve understanding or change an evidence judgment. If the source bundle is missing or extraction fails, record the limitation and continue from the PDF rather than inventing a replacement.

Reuse an existing workspace for the same paper unless the user requests a separate version. Never write generated paper workspaces inside the installed skill directory.
Do not pass `--force` unless the user has explicitly confirmed that replacing the existing `report.md` is acceptable.

### 6. Build the Paper's Mental Model

Before judging the paper, establish:

1. the question or problem;
2. why the problem matters within the paper's own framing;
3. the central idea, thesis, or mechanism;
4. the structure connecting premises, method, evidence, and conclusion;
5. the minimum concepts, notation, and prior work needed to follow that structure.

Also place the paper in context when the source permits it: record its problem route, main assumptions, evaluation or support route, contribution type, similar or contrasting works actually identified from the paper, and the most important gap it leaves. Do not turn this single-paper step into a broad literature review.

Use a small example when it materially improves understanding. Do not introduce examples that silently change the paper's assumptions.

### 7. Extract Claims and Evidence

Read `references/evidence-policy.md` before assigning claim categories, support strength, source locations, or verdicts.

Build a claim record for every central conclusion and any subordinate claim required to support it. Each record must contain:

- `claim_id`;
- the authors' claim in faithful paraphrase;
- claim category: explicit claim, source-backed implication, or report inference;
- source location;
- evidence type;
- evidence summary;
- support strength;
- largest gap or uncertainty;
- verdict.

Use evidence appropriate to the paper:

- experiments, effect sizes, controls, statistics, robustness checks, and failure cases;
- definitions, assumptions, lemmas, theorems, proof steps, counterexamples, and complexity bounds;
- datasets, splits, protocols, leakage checks, benchmarks, interfaces, system tests, and implementation details;
- premises, conceptual distinctions, textual support, objection handling, counterarguments, and inferential validity;
- review scope, search strategy, inclusion criteria, synthesis method, coverage, heterogeneity, and publication bias.

Use actions such as `supported`, `partially_supported`, `not_established`, `contradicted`, or `not_verifiable_from_available_source` rather than unanchored numerical scores.

For each central claim, record the strongest safe version, wording that would overstate the evidence, and whether the claimed result is demonstrated, planned, assumed, interpreted, or unavailable. Use the claim-safety table in `assets/report-template.md`; its adapted third-party provenance is recorded in `references/third-party-notices.md`.

Review `evidence/claims.json` after the preprocessing pipeline. Set each record to `keep` or `discard`; never leave a final record `pending`. For kept claims, review the adjacent source blocks, complete every evidence and boundary field, then validate:

```bash
python3 "<skill-root>/scripts/claim_records.py" apply-review \
  --workspace "<paper workspace>" \
  --review "<compact review overlay.json>"

python3 "<skill-root>/scripts/claim_records.py" validate \
  --workspace "<paper workspace>"
```

Use a compact review overlay with `discard_unlisted: true` and a non-empty `discard_reason` when only a small set of candidates are central; list complete reviewed fields only for kept claims. Put central claims missed by cue retrieval in the overlay's `new_claims` list with a unique claim ID, valid source locator, and complete reviewed fields. The command preserves raw candidates, constructs adjacent context for new records, and merges decisions into `evidence/claims.json`. Do not use the claim records as final report evidence while `evidence/claim-validation.json` has `passed: false`. Never force an unrelated candidate to fit.

### 8. Apply Type-Specific Review Standards

For experimental or social-science empirical papers, check design, sampling, measurement, controls, statistical uncertainty, alternative explanations, robustness, and external validity.

For technical or method papers, check input-output semantics, mechanism, training and inference differences, baselines, ablations, data leakage, implementation details, resource cost, and failure conditions.

For theoretical or mathematical papers, check definitions, assumptions, theorem scope, proof dependencies, missing cases, counterexamples, and the distance between formal results and informal claims.

For systems, benchmarks, platforms, or datasets, check interfaces, protocol, dataset construction, splits, coverage, leakage, fairness, system tests, costs, and reproducibility.

For reviews and meta-analyses, check scope, search and inclusion rules, material coverage, synthesis method, heterogeneity, bias, omissions, and whether the conclusions exceed the included evidence.

For philosophy or humanities argument papers, check thesis clarity, conceptual distinctions, premises, inferential steps, textual or historical support, objections, counterexamples, and whether the conclusion exceeds the argument. Absence of experiments is not itself a defect.

### 9. Write the Report

Use the report template in `assets/report-template.md` when available. Keep the following order:

1. Three-minute understanding;
2. Paper identity and access boundary;
3. Research question, thesis, and field position;
4. Essential concepts and terms;
5. Method, theory, or argument structure;
6. Central claims and evidence;
7. Necessary figures, tables, formulas, or key passages;
8. Contributions and genuine novelty;
9. Limitations, objections, and unresolved questions;
10. Final reading judgment and recommended next actions;
11. Evidence index.

Adapt depth to the reading mode. A quick read may compress sections, but it must retain the central conclusion, decisive evidence, and access boundary. A critical review may expand the claim-evidence table and objections. Do not omit a central claim merely to shorten the report.

Use figures, tables, formulas, or quotations only when they improve understanding or alter a judgment. Keep them near the explanation they support. Respect quotation limits and prefer faithful paraphrase.

### 10. Validate Before Delivery

Run the bundled final validator:

```bash
python3 "<skill-root>/scripts/validate_report.py" \
  --workspace "<paper workspace>" \
  --final
```

Require both `evidence/claim-validation.json` and `evidence/validation.json` to have `passed: true` for a final full-text report. Do not deliver while either gate is false. Fix every error and rerun validation. Review warnings individually; keep a warning only when the report already states the corresponding boundary and the issue does not invalidate a central judgment. The report validator reuses duplicate-paragraph, image-path, encoding, and math-compatibility checks from `sodalone/paper-reading-skill`, with cross-disciplinary report rules adapted for this skill.

Before delivering, verify that:

- the opening summary is understandable without undefined terms;
- the report explains the paper before judging it;
- the abstract, introduction, conclusion, and central results or argument sections are represented;
- each consequential judgment has a source location or an explicit uncertainty label;
- author claims and report inferences are visibly distinct;
- no unsupported numbers, citations, quotations, or bibliographic fields were invented;
- the evaluation criteria match the paper type;
- the report contains no placeholders or broken relative paths;
- the declared access level matches what was actually read;
- `report.md` remains the single primary report.

Deliver a concise chat summary and the complete Markdown report. Mention material extraction or access limitations in both.

## Human Confirmation Gates

Pause only for a consequential decision:

- multiple papers plausibly match a title;
- the user must choose between meaningfully different reading goals;
- only an abstract is available but the user requested a full review;
- the source is unreadable or access requires authority the user has not granted;
- continuing would overwrite a user-modified report.

Otherwise continue with an explicit default. If the user delegates a decision, record the assumption in `metadata.json` and keep uncertain conclusions provisional.

## Boundaries

- Handle one focal paper per run. Route multi-paper field mapping or literature-review requests to an appropriate multi-paper workflow.
- Do not write a submission-ready paper on the user's behalf under the guise of reading assistance.
- Do not fabricate full text, citations, page numbers, figures, equations, results, or reviewer comments.
- Do not treat publisher prestige, citation count, or confident prose as evidence that a claim is correct.
- Do not infer that a missing conventional section is a defect when the paper type does not require it.
