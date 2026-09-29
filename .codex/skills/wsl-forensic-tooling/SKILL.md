---
name: wsl-forensic-tooling
description: Check and, after explicit authorization, install cataloged WSL forensic-tool dependencies for Nexus-Lab. Use when a required forensic command is missing; do not use to select an examination method or install unreviewed software.
---

# WSL forensic tooling

Use the repository `wsl-requirements.txt` as the allowlisted dependency catalog.

1. Confirm the required capability follows from the examination question and selected method. Do not install the whole catalog.
2. Run `Lab/scripts/check-wsl-tools.sh` inside WSL to check availability without changing the system.
3. If the selected row uses `method=apt`, use `apt-get --simulate install PACKAGE=VERSION` to inspect dependencies without changing the system. Report the exact tool ID, package, candidate version from the check, distribution, command, network use, privilege requirement, and simulated system changes. Obtain explicit user authorization for that installation and version. If no candidate is reported, stop; refreshing package metadata is a separate networked system change that must be disclosed and authorized.
4. Only after that authorization, run `Lab/scripts/install-wsl-tool.sh --authorized TOOL_ID EXPECTED_VERSION` inside WSL. The installer pins the authorized version and stops if the candidate changed. Never treat an earlier examination authorization or the `--authorized` flag itself as consent.
5. Preserve the installation log emitted below `Lab/logs/tool-installations/` and report failures without silently changing repositories or retrying with another method.
6. If the row uses `method=manual`, read [references/manual-installation.md](references/manual-installation.md) and prepare a separate, version-specific plan. Do not download or install until the user authorizes that exact plan and its network access.

Package installation does not authorize mounting, acquisition, live capture, device access, execution of evidence content, or any examination step. Apply the repository `AGENTS.md` boundaries throughout.
