# Report structure

Use the smallest structure that answers the case question while preserving independent scrutiny:

1. Identification, version, author, reviewer, and dates.
2. Authority, scope, questions, assumptions, and exclusions.
3. Evidence inventory, custody references, and integrity verification.
4. WSL environment, methods, tools, versions, validation basis, and deviations.
5. Findings, each carrying its epistemic state and source, with observations separated from derivations, inferences, alternatives, confidence, and conclusions.
6. Timeline or correlation results when relevant.
7. Limitations, errors, inaccessible or encrypted data, and material negative findings.
8. Conclusion bounded by the stated scope.
9. Appendices containing commands, logs, hashes, generated-file inventory, and terminology.

Never leave a required factual field silently implied or populate it with a likely value. Use `unknown` when the value is unavailable, `not observed` only after a successful defined search within known coverage, and `not determined` when evidence or method is insufficient. Attribute reported information to its provider. For derived values, cite the inputs and preserved calculation. For every inference, cite supporting observations and state assumptions, alternatives, limitations, and confidence.

Use stable IDs rather than ambiguous filenames. A conclusion must trace through finding → artifact → tool run → verified working copy → evidence item.
