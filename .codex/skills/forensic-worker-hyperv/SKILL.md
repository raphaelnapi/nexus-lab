---
name: forensic-worker-hyperv
description: Plan, validate, or operate an approved Nexus-Lab v2 Linux Hyper-V worker job for a method without a trusted Windows provider. Do not provision, network, install, or discard worker state without explicit authority.
---

# Forensic Hyper-V worker

Read [worker controls](../../../docs/hyperv-worker.md). Require a method pack whose backend is `hyperv-worker`, an active approval, a recorded base-image hash, an isolated internal switch, a per-job differencing disk, and validated guest tools.

Copy only verified working copies into staging. Verify hashes on host and guest. Keep external networking disabled. Transfer outputs back, verify and register them before any authorized cleanup or rollback. Preserve guest command, version, stdout/stderr, exit status, timestamps, image/checkpoint identity, transfer hashes, errors, and limitations.

If Hyper-V, isolation, SSH identity, tool validation, or hash agreement is unavailable, stop and mark the capability unavailable.

