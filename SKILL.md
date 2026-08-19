---
name: deep-paper-reader
description: Read, explain, and critically review one academic paper with traceable evidence. Use when a user provides a local PDF, direct PDF URL, arXiv link or ID, DOI, or identifiable paper title and asks for a quick read, deep read, structured explanation, critical review, claim verification, method or argument analysis, or a reusable Markdown reading report. Support experimental, technical, theoretical, mathematical, systems, dataset, review, humanities, philosophy, and social-science papers. Do not use for multi-paper literature reviews, unsupported paper writing, or analysis without access to at least the abstract; never imply full-text review when only metadata or an abstract is available.
---

# Deep Paper Reader

## Overview

Turn one academic paper into an understandable, evidence-grounded, reusable reading report. Match the reading method to the paper type, distinguish the authors' claims from the report's inferences, and preserve source locations for every conclusion that could change the reader's judgment.

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

Reuse an existing workspace for the same paper unless the user requests a separate version. Never write generated paper workspaces inside the installed skill directory.

### 6. Build the Paper's Mental Model

Before judging the paper, establish:

1. the question or problem;
2. why the problem matters within the paper's own framing;
3. the central idea, thesis, or mechanism;
4. the structure connecting premises, method, evidence, and conclusion;
5. the minimum concepts, notation, and prior work needed to follow that structure.

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
3. Research question or thesis;
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
