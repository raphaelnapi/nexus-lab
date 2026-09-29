---
name: timeline-analysis-wsl
description: Build and interpret forensic timelines from registered artifacts using WSL tools while preserving source time semantics. Use for event correlation; do not use when time zones or provenance are unknown and undocumented.
---

# Timeline analysis with WSL

Read [references/timeline-method.md](references/timeline-method.md) and apply `forensic-tool-runner-wsl` for extraction and sorting tools.

1. Record the source clock, timezone, daylight-saving rules, known skew, timestamp resolution, and parser behavior.
2. Preserve each original timestamp value and representation before normalization.
3. Normalize comparison values to UTC, retaining the source timezone and transformation rule.
4. Attach every event to its evidence, artifact, parser, and precise locator.
5. Correlate independent sources and expose conflicts instead of silently choosing one.
6. Distinguish event occurrence time, recording time, collection time, and analysis time.
7. State uncertainty and avoid causal conclusions based solely on temporal proximity.
