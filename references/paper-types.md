# Paper-Type Routing Guide

## Purpose

Use this guide after resolving the paper and before extracting claims. Select one primary type and only the secondary types needed to evaluate central claims. Classification controls the evidence route; it does not force a fixed report length.

## Classification Signals

| Paper type | Common signals | Primary question |
|---|---|---|
| Experimental or observational | participants, samples, interventions, measurements, statistical analysis | Does the design and evidence support the empirical conclusion? |
| Technical or method | model, algorithm, architecture, objective, training, inference, baseline | Does the proposed mechanism cause the reported improvement under a fair comparison? |
| Theoretical or mathematical | definitions, assumptions, lemmas, theorems, proofs, bounds | Does the conclusion follow within the stated formal scope? |
| System or platform | architecture, interface, deployment, latency, throughput, system evaluation | Does the implemented system behave as claimed under the reported conditions? |
| Benchmark or dataset | collection, annotation, splits, metrics, coverage, leakage | Does the resource measure or represent what the authors claim? |
| Literature review | search scope, inclusion criteria, coding, synthesis, research landscape | Does the selected literature support the synthesis? |
| Systematic review or meta-analysis | protocol, database search, screening, effect size, heterogeneity | Is the pooled conclusion justified by the included studies and synthesis method? |
| Philosophy or humanities argument | thesis, concepts, premises, interpretation, objections, textual evidence | Does the conclusion follow from defensible premises and interpretations? |
| Social-science conceptual | constructs, framework, mechanisms, propositions, cases | Are the concepts coherent and the proposed relations adequately grounded? |

## Evidence and Review Routes

### Experimental or Observational Study

Inspect:

- research design and identification strategy;
- sample selection and representativeness;
- measurement validity and reliability;
- controls, confounders, and alternative explanations;
- effect size, uncertainty, robustness, and missing data;
- difference between association, prediction, and causation;
- population and setting to which the result may generalize.

Do not treat statistical significance alone as practical importance or causality.

### Technical or Method Paper

Inspect:

- task definition, inputs, outputs, and target failure;
- mechanism and difference from the closest baseline;
- training, inference, and data-processing semantics;
- baseline fairness and hyperparameter treatment;
- ablations that isolate the claimed mechanism;
- generalization, failure cases, resource cost, and implementation details;
- whether reported gains match the breadth of the authors' claim.

Do not infer mechanism from aggregate performance alone.

### Theoretical or Mathematical Paper

Inspect:

- definitions and hidden regularity assumptions;
- theorem statement and quantifier scope;
- lemma and proof dependencies;
- omitted cases, degenerate cases, and counterexamples;
- computational or sample-complexity assumptions;
- distance between the formal result and informal claims in the introduction.

Do not criticize the absence of experiments when the central contribution is formal.

### System, Platform, Benchmark, or Dataset

Inspect:

- system boundary, interface, protocol, and implementation path;
- dataset origin, composition, annotation, splits, and licenses;
- benchmark construct validity and metric behavior;
- contamination, leakage, fairness, and subgroup coverage;
- latency, throughput, reliability, cost, and failure recovery;
- reproducibility assets and version-specific behavior.

Do not treat a benchmark score as proof of real-world usefulness without a valid task-to-use-case link.

### Review or Meta-Analysis

Inspect:

- review question and temporal or disciplinary boundary;
- databases, queries, inclusion and exclusion rules;
- screening, coding, and quality assessment;
- synthesis method, heterogeneity, and publication bias;
- influential omissions and conflicting evidence;
- whether conclusions exceed the reviewed material.

Do not call a narrative overview systematic unless the paper reports a reproducible protocol.

### Philosophy or Humanities Argument

Inspect:

- thesis and the exact question being answered;
- definitions and conceptual distinctions;
- explicit and implicit premises;
- inferential steps from premises to conclusion;
- primary-text, historical, interpretive, or conceptual support;
- objections, counterexamples, rival interpretations, and replies;
- whether the conclusion is stronger than the argument establishes.

Do not substitute author reputation, canonical status, or quotation volume for argumentative support.

### Social-Science Conceptual Paper

Inspect:

- construct definitions and boundary conditions;
- relation between concepts, mechanisms, and propositions;
- connection to prior evidence or cases;
- alternative frameworks and discriminating predictions;
- operationalizability and implications for future research.

Do not treat a plausible diagram or taxonomy as an empirically established mechanism.

## Hybrid Papers

Use a secondary route only for a central claim that genuinely depends on it. Examples:

- a method paper with a convergence theorem: technical primary, theoretical secondary;
- a philosophy paper using survey evidence: philosophy primary, empirical secondary;
- a dataset paper proposing a new metric: dataset primary, theoretical or empirical secondary;
- a systematic review advancing a conceptual framework: review primary, conceptual secondary.

Record why each secondary type is necessary. Do not combine routes merely because the paper contains a formula, table, quotation, or appendix.

## Classification Confidence

Record classification confidence as `high`, `medium`, or `low` with a one-sentence reason. If low confidence changes the review criteria, ask the user or keep the verdict provisional.
