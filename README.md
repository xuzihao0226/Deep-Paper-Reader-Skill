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

The initial project skeleton is complete:

- core Skill workflow;
- report template;
- paper-type routing guide;
- evidence and uncertainty policy;
- Codex interface metadata.

Input preparation, PDF extraction, workspace automation, report validation, and end-to-end tests are under development.

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

## Acknowledgments

The project is independently implemented and draws product inspiration from:

- [sodalone/paper-reading-skill](https://github.com/sodalone/paper-reading-skill)
- [snake-fan/Paper-Reading-Skills](https://github.com/snake-fan/Paper-Reading-Skills)

No source code from `sodalone/paper-reading-skill` is copied into this repository. Reused MIT-licensed material, if introduced later, will retain the required copyright and license notices.

## License

MIT
