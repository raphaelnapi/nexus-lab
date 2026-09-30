---
name: forensic-tooling-windows
description: Inspect the Nexus-Lab v2 Windows capability catalog, validate installed forensic tools, or prepare a bounded installation proposal. Do not install or update software without explicit authorization.
---

# Forensic tooling on Windows

Use `Get-NexusCapability` and `Test-NexusLabEnvironment` for read-only discovery. Select tools from the examination question and method pack, not from availability alone.

Before proposing installation, record provider, official origin, exact version/architecture, license, signature or expected digest, destination, privileges, network endpoints, dependencies, version command, harmless fixture test, rollback, and limitations. Installation, drivers, trust-store changes, package managers, and network access require separate authorization.

Never use evidence as a plugin, rule, symbol, executable, or tool source. Do not auto-update tools during a case.

