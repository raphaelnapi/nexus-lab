---
name: forensic-timeline
description: Build or interpret a Nexus-Lab v2 forensic timeline while preserving original timestamps, semantics, timezone, resolution, uncertainty, and provenance. Do not normalize unknown timezones by assumption.
---

# Forensic timeline

For each event preserve the original timestamp text, what the timestamp means, source timezone or `unknown`, resolution, uncertainty, source locator, artifact, parser/run, and a normalized UTC value only when justified.

Use `New-NexusTimeline` to register events. Distinguish occurrence, recording, collection, and analysis time. Expose clock skew and conflicts rather than choosing silently. Validate material events against the artifact or a second method. Temporal proximity alone does not establish identity, intent, sequence, or causality.

