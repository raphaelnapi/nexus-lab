---
name: evidence-intake-windows
description: Register, hash, verify, or prepare a working copy of evidence in a configured Nexus-Lab v2 Windows workspace. Do not use for physical acquisition or for reorganizing evidence.
---

# Evidence intake on Windows

Confirm the active case, evidence ID, provider-attributed information, source state, operator, write protection, and intended action. Resolve the source below the configured evidence root and stop on ambiguity, reparse traversal, unexpected writability, or identity change.

Use `Register-NexusEvidence` for read-only SHA-256/SHA-512 registration and `Test-NexusEvidence` for verification. A working copy is a separate, explicitly authorized action through `New-NexusWorkingCopy`; verify its hashes before examination.

Never write sidecars, temporary files, streams, metadata, or logs below the evidence root. A normal copy is not physical forensic acquisition. Read [operations](../../../docs/operations.md) when a working copy is requested.

