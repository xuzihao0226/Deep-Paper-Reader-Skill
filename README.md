# Deep Paper Reader Skill

> An evidence-grounded Codex Skill for understanding and critically reviewing one academic paper across disciplines.

Deep Paper Reader turns a local PDF, direct PDF URL, arXiv paper, DOI, or identifiable paper title into a structured Markdown reading report. It is designed for quick reading, deep reading, and critical review while keeping consequential conclusions traceable to the source.

## Why This Project

Many paper-reading tools summarize content but blur the difference between an author's claim, the paper's evidence, and the model's own inference. Deep Paper Reader treats that distinction as a product requirement.

The project aims to support technical, experimental, theoretical, mathematical, systems, dataset, review, philosophy, humanities, and social-science papers without forcing every discipline into the same evaluation template.

## Planned Workflow

```text
Paper input
→ source and access check
→ reading-mode selection
→ paper-type classification
→ text and evidence extraction
→ claim-evidence review
→ structured Markdown report
→ final validation
```

## Reading Modes

- `quick_read`: understand the problem, central idea, conclusion, decisive evidence, and reading value;
- `deep_read`: build a systematic understanding of concepts, structure, methods or arguments, evidence, contributions, and limitations;
- `critical_review`: test whether central claims are adequately supported and identify the most consequential gaps.

## Current Status

The project now includes:

- core Skill workflow;
- report template with paper-position and claim-safety records;
- paper-type routing guide;
- evidence and uncertainty policy;
- Codex interface metadata;
- workspace preparation for local PDF, PDF URL, arXiv, DOI, publisher page, or title input;
- source acquisition with verified PDF detection and explicit access-status recording;
- page-aware PDF text extraction with stable evidence locators and OCR warnings;
- heuristic section reconstruction and traceable claim-candidate retrieval;
- source-first arXiv figure extraction with LaTeX caption and section context;
- formal claim-evidence review records with controlled verdicts, source-locator checks, and an explicit human decision gate;
- compact review overlays that keep central claims, add important claims missed by retrieval, and safely discard unlisted candidates without editing large evidence files by hand;
- a cross-platform Python pipeline that runs deterministic preprocessing from paper input through claim-review preparation;
- final report validation for structure, evidence locations, images, encoding, duplication, and math compatibility;
- automated workspace regression tests.

Real-paper forward evaluations now cover both humanities argumentation and a long technical tutorial review. Further report-writing assistance remains under development. Final scholarly judgments stay human- or agent-reviewed rather than being assigned by cue matching alone.

## Current Executable Workflow

```bash
python3 scripts/run_pipeline.py \
  --paper "<paper input>" \
  --output-root "<output directory>" \
  --mode deep_read
```

The unified pipeline prepares the source, traceable text, reading map, figures, and `evidence/claims.json`, then deliberately stops at `ready_for_claim_review`. Review each proposed claim and its adjacent source context before continuing:

```bash
python3 scripts/claim_records.py apply-review \
  --workspace "<generated paper workspace>" \
  --review "<compact review overlay.json>"

python3 scripts/claim_records.py validate \
  --workspace "<generated paper workspace>"

python3 scripts/validate_report.py \
  --workspace "<generated paper workspace>" \
  --final
```

Use `python3 scripts/run_pipeline.py --resume-workspace "<workspace>"` to continue an interrupted workspace without replacing existing manual claim decisions. The earlier individual commands remain available when a stage needs to be run or debugged separately.

The first real-paper forward test used Henrik Bohlin's 2009 philosophy article *Sympathy, Understanding, and Hermeneutics in Hume’s Treatise*. It exposed and led to fixes for alternating journal headers, numbered footnotes misread as headings, over-broad claim retrieval, and cumbersome manual review. The revised run detected 11 document sections, produced 40 ranked candidates, retained 8 central reviewed claims, and passed both evidence and final-report validation without warnings. The copyrighted paper and generated reading workspace are not included in this repository.

The second forward test used Kevin P. Murphy's 253-page arXiv tutorial *Reinforcement Learning: An Overview* through its DOI. It verified DOI-to-arXiv acquisition, source-bundle figure extraction, and long-document review routing. The test also exposed page-number-only leaves being treated as failed extraction, pseudocode and formulas being misread as headings, and local chapter descriptions being promoted over review-level scope claims. The revised run classified six leaves as intentional blanks, reconstructed 227 sections, extracted 62 figures, reviewed 40 retrieval candidates, added 8 central paper-level claims through a compact overlay, and passed both validation gates without warnings. The paper and generated workspace are not included in this repository.

The source resolver supports local Portable Document Format (PDF) files, direct PDF URLs, arXiv links or IDs, Digital Object Identifier (DOI) records, and publisher landing pages. A title-only input is deliberately routed to authoritative identity search instead of being matched automatically. The figure extractor runs when an arXiv source bundle is available.

Run all automated tests from the repository root with:

```bash
python3 -m unittest discover -s scripts -p 'test_*.py'
```

## Repository Structure

```text
.
├── SKILL.md
├── README.md
├── LICENSE
├── agents/
├── assets/
├── references/
└── scripts/
```

## Example Request

```text
Use $deep-paper-reader to deeply read this paper and produce a Chinese report with traceable evidence.
```

## Design Principles

- explain before evaluating;
- match evidence standards to the paper type;
- distinguish author claims from report inferences;
- expose access and extraction limitations;
- preserve a single reusable Markdown report;
- ask for human confirmation only when a decision materially changes the result.

## License

MIT
