---
name: evidence-intake-wsl
description: Register, hash, verify, and prepare working copies of digital evidence in Nexus-Lab using WSL tools. Use for evidence intake or integrity verification; never use to modify, reorganize, or clean Evidence.
---

# Evidence intake with WSL

Read [references/intake-workflow.md](references/intake-workflow.md) before handling a new item.

1. Confirm case ID, authority, source, operator, received state, and intended action.
2. Verify that the source resolves below `Evidence/` and destinations resolve below the active `Lab/` or `Registry/` case.
3. Check WSL and required tools. Do not install dependencies without explicit authorization.
4. Inventory and hash the source read-only. Use the repository hashing helper for regular files.
5. Acquisition, copying, mounting, or permission changes require explicit user authorization.
6. After an authorized copy, hash it independently and compare it with the registered source hash.
7. Stop on mismatch, source mutation, ambiguous identity, or a destination outside the active case.

Never use shell redirection, temporary files, or sidecar metadata inside `Evidence/`.
