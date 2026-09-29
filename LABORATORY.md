# Nexus-Lab

Nexus-Lab is a local workspace for controlled digital-evidence examination with Codex orchestration and forensic tooling executed in WSL 2.

This structure supports a documented method; it does not by itself establish legal admissibility, laboratory accreditation, or compliance with a jurisdiction-specific procedure.

## Security zones

| Zone | Purpose | Write policy |
|---|---|---|
| `Evidence/` | Received evidence and forensic images | Read-only to the agent and analysis tools |
| `Lab/` | Verified working copies, derived data, analysis, and reports | Writable within the active case |
| `Registry/` | Case metadata, hashes, custody events, and audit records | Append or create a new version; do not silently overwrite |

The Windows read-only attribute is not a security boundary. Protect evidence with NTFS permissions, storage controls, write blockers when applicable, verified hashes, and a Codex sandbox that does not grant write access to `Evidence/`. Do not deny the analyst account write access until the evidence-ingestion procedure has been decided, because Codex currently runs under that same account.

## WSL status and prerequisites

At initialization time WSL 2 was enabled, but no Linux distribution was installed. Installations and package changes require explicit user authorization.

Once a distribution exists, run the environment check from the repository root:

```powershell
wsl.exe --cd "C:\Users\rapha\Desktop\PV Forense\Nexus-Lab" -- bash Lab/scripts/check-environment.sh
```

The check reports, but does not install, common dependencies. Tool choice remains case-specific.

Cataloged WSL dependencies are declared in `wsl-requirements.txt`. Missing tools
may be checked with `Lab/scripts/check-wsl-tools.sh`. Installation is deliberately
separate: the `wsl-forensic-tooling` skill may install an allowlisted `apt` package
only after explicit authorization for the named package, network use, privilege,
and system change. Tools marked `manual` require a version-specific review and
separate authorization; the catalog is not standing permission to install.

## Case lifecycle

1. Assign a stable case ID and document authority, scope, operator, and time reference.
2. Register the received item and its state before examination.
3. Identify and acquire data using an approved, documented method.
4. Hash the source or forensic image and verify the working copy.
5. Analyze only the verified working copy under `Lab/cases/<case-id>/`.
6. Record every method, tool version, command, input, output, time, result, and limitation.
7. Separate observations from interpretations and link findings to precise evidence locators.
8. Validate the results, preserve generated-file hashes, and produce a reviewable report.

## Case layout

`Lab/scripts/new-case.sh CASE-YYYY-NNNN` creates:

```text
Lab/cases/CASE-YYYY-NNNN/
├── 00-administrative/
├── 01-working-copies/
├── 02-extracted/
├── 03-analysis/
├── 04-timelines/
├── 05-reports/
├── 06-exports/
├── database/case.sqlite3
└── logs/

Registry/CASE-YYYY-NNNN/
```

The SQLite schema is authoritative for structured case data. The CSV files in `Lab/templates/` are interchange templates, not a substitute for integrity controls.

## Python tooling

Reusable Python code lives in `Lab/python/nexus_lab/`, command-line entry points
in `Lab/scripts/python/`, and tests in `Lab/tests/python/`. The legacy command
`Lab/scripts/hash-evidence.py` remains as a compatibility wrapper; new automation
should use `Lab/scripts/python/hash_evidence.py`.

Runtime dependency declarations live in `Lab/requirements/`. Use an isolated
virtual environment and do not install or update packages without explicit
authorization. Record exact versions, hashes, origin, and the installation
command. Python tools must never import or execute code recovered from evidence,
must not overwrite inputs, and may write only to authorized `Lab/` or `Registry/`
paths.

Run the standard-library test suite from the repository root with:

```powershell
python -m unittest discover -s Lab/tests/python -v
```

## Methodological basis

- [ISO/IEC 27032:2023](https://www.iso.org/standard/76070.html): cybersecurity and Internet-security context, stakeholders, roles, coordination, and controls relevant to the laboratory.
- [ISO/IEC 27042:2015](https://www.iso.org/standard/44406.html): analysis and interpretation of digital evidence, including continuity, validity, repeatability, reproducibility, method selection, and independent scrutiny.

The project records its alignment with those principles but must not claim ISO certification or full conformity without the licensed standards, a formal gap assessment, and the required organizational controls.
