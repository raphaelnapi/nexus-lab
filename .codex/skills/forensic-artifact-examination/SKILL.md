---
name: forensic-artifact-examination
description: Select and conduct a bounded examination of verified disk, Windows, memory, document/PDF, or PCAP artifacts in Nexus-Lab v2. Do not use for live response, acquisition, or final legal conclusions.
---

# Forensic artifact examination

Define the question and coverage, then read only the relevant reference:

- Disk images and filesystems: [disk.md](references/disk.md)
- Windows Registry and EVTX: [windows.md](references/windows.md)
- Memory: [memory.md](references/memory.md)
- Documents and PDFs: [documents.md](references/documents.md)
- Packet captures: [network.md](references/network.md)

Work only from verified copies. Prefer a validated Windows provider; use the Hyper-V worker only when the method pack declares it. Extract the smallest justified subset and retain exact locators, parser/version, warnings, unsupported regions, and negative-result coverage.

Parser output is not automatically a fact about the source. Validate material observations and keep observation, derivation, inference, and conclusion separate.

