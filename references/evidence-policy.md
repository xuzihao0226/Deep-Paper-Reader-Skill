# Evidence and Uncertainty Policy

## Purpose

Use this guide before building the claim-evidence table and again during final validation. The goal is not to maximize criticism; it is to make every consequential judgment proportionate to the available source.

## Claim Categories

Label every claim as exactly one category:

- `explicit_author_claim`: directly asserted by the authors;
- `source_backed_implication`: not stated verbatim, but follows closely from identified source material;
- `report_inference`: an interpretation or judgment introduced by the reading report.

Never rewrite a report inference as an author claim. When wording is ambiguous, prefer the weaker category and explain why.

Items in `evidence/claim_candidates.json` are retrieval hints, not claim records. Review the surrounding source blocks, identify the speaker, preserve negation and scope, and confirm that the statement matters to the paper's main line before assigning a claim category or verdict.

## Source Locations

Use the most stable locator available:

1. named section or subsection plus paragraph context;
2. PDF page plus the extracted `P###-B###` block locator when available;
3. PDF page and printed page when both exist;
4. figure, table, equation, theorem, proposition, example, or appendix identifier;
5. quoted opening words for unnumbered passages;
6. abstract-only label when full text is unavailable.

A location must allow another reader to find the evidence without rereading the entire paper. Do not invent paragraph or page numbers.

For HTML and PDF versions with different pagination, name the version used. For scanned papers, note that page locations refer to the PDF image pages.

## Evidence Record

Each evidence item must include:

- `evidence_id`;
- linked `claim_id` values;
- source version;
- source type;
- exact location;
- faithful paraphrase or a short compliant quotation;
- relevance to the claim;
- limitation or ambiguity.

Keep raw extraction separate from interpretation. The evidence summary should describe what the source shows; the verdict should state what follows from it.

## Verdict Rules

### `supported`

Use only when the relevant evidence directly addresses the claim, appropriate alternatives have been handled for the claim's scope, and no identified gap would materially reverse the conclusion.

### `partially_supported`

Use when evidence supports a narrower, conditional, or weaker version of the claim, or when one necessary component is established but another remains uncertain. State the strongest safe version.

### `not_established`

Use when the paper makes the claim but the presented evidence is insufficient, indirect, underidentified, logically incomplete, or mismatched to the claim. This does not mean the claim is false.

### `contradicted`

Use only when available evidence conflicts with the claim under the same definitions and scope. Distinguish genuine contradiction from a different population, task, interpretation, or assumption set.

### `not_verifiable_from_available_source`

Use when the needed section, appendix, data, proof, code, or full text is unavailable or unreadable. Do not downgrade this to `not_established` unless the paper itself fails to provide required evidence.

## Support Strength

Describe support with anchored language rather than decimal scores:

- `direct_and_decisive`;
- `direct_but_limited`;
- `indirect`;
- `conflicted`;
- `missing`;
- `unavailable`.

The label describes the evidence-to-claim relationship, not the prestige of the venue or the reader's agreement with the conclusion.

## Access Boundaries

### Full Text

Full-text access permits a report to evaluate all central claims only after checking the relevant body sections and appendices. Merely downloading a PDF does not prove that extraction succeeded.

### Partial Text

List available and unavailable sections. Restrict verdicts to what can be checked. Mark any conclusion depending on missing material as provisional or not verifiable.

### Abstract Only

Provide only:

- bibliographic identity;
- the authors' stated problem, approach, and conclusion;
- an explicit list of unverified items;
- a recommendation about obtaining the full text.

Do not evaluate experiments, proofs, novelty, limitations, or reliability as though the paper were read in full.

## Inference Discipline

- Use "the authors argue/report" for explicit claims.
- Use "the source suggests" for close implications.
- Use "this report infers" for report-level interpretation.
- Use "cannot be determined from the available source" when access is the limiting factor.
- Use "the paper does not establish" only when the relevant full-text evidence has been checked.

Do not convert absence of mention into evidence of absence unless the paper's design makes the omission probative.

## External Sources

Use external sources only when they are necessary to check novelty, contested background, implementation behavior, corrections, retractions, or decisive alternative evidence. Record direct links and distinguish external evidence from the focal paper's evidence.

Do not use snippets, unsourced summaries, or search-result text as decisive evidence. Prefer the original paper, official correction or retraction notice, repository, dataset documentation, or primary scholarly source.

## Quotations and Paraphrases

Prefer faithful paraphrase. Quote only when exact wording is necessary for a conceptual, interpretive, or definitional point. Keep quotations short, preserve context, and attach an exact locator.

Never reconstruct unreadable text, equations, numbers, or citations from context.

## Final Evidence Audit

Before delivery, confirm:

- every central claim has at least one evidence record or an explicit unavailable-evidence label;
- every verdict follows the rules above;
- author claims and report inferences remain distinct;
- the report's access level matches the material actually read;
- no source locator, number, quotation, or citation was invented;
- limitations describe their effect on the conclusion rather than merely listing generic weaknesses.
