---
name: artifact-triage-wsl
description: Perform a bounded, read-only first-pass triage of verified disk images or extracted data using WSL forensic tools. Use to inventory and prioritize artifacts; do not use for acquisition or final conclusions.
---

# Artifact triage with WSL

Read [references/triage-method.md](references/triage-method.md) and use `forensic-tool-runner-wsl` controls for every execution.

1. Define the triage question and limits before selecting tools.
2. Work from a verified working copy; preserve its hash and format details.
3. Begin with container, partition, filesystem, and basic metadata inventory.
4. Extract only what is necessary into `02-extracted/`; place analyses in `03-analysis/`.
5. Record negative results, parser errors, unsupported structures, encryption, and inaccessible regions.
6. Treat triage as prioritization. Do not equate absence in a parser's output with absence from the evidence.

Stop if a tool attempts a write, the image mapping differs from expectations, or integrity verification fails.
