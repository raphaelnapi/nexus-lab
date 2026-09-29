---
name: forensic-reporting
description: Produce a reviewable Nexus-Lab forensic report from registered WSL examination records. Use for technical findings and final reports; do not invent missing provenance or present hypotheses as facts.
---

# Forensic reporting

Read [references/report-structure.md](references/report-structure.md) before drafting.

1. Use the case database, registered artifacts, attributed reported information, and preserved tool runs as sources. Never fill missing values from plausibility, templates, or model knowledge.
2. State authority, scope, questions, evidence, integrity verification, environment, methods, and deviations.
3. Preserve the epistemic state defined by `forensic-methodology`: reported, observed, derived, inferred, concluded, unknown, not observed, or not determined. Present observations separately from interpretations and conclusions.
4. Cite evidence IDs, hashes, artifact IDs, precise locators, tool runs, and report attachments.
5. Include alternative explanations, confidence, limitations, inaccessible data, errors, and negative results relevant to the question. State negative findings only within the recorded method coverage.
6. Make the report independently reviewable without exposing secrets or unnecessary personal data.
7. Hash the final report and register it as a generated file. Never claim ISO certification or legal admissibility.
