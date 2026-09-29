---
name: forensic-tool-runner-wsl
description: Plan and run an authorized forensic command in WSL with provenance, logging, and case-scoped outputs. Use when executing a forensic tool; do not use to install tools or run extracted evidence binaries.
---

# Forensic tool execution in WSL

Read [references/execution-record.md](references/execution-record.md) before executing a tool.
When working with PDF documents or digital signatures, also read [references/pdf-and-signatures.md](references/pdf-and-signatures.md).

1. Confirm the active case, question, verified input, expected outputs, and authorization.
2. Confirm the input is a working copy or an explicitly approved read-only source.
3. Resolve all paths before execution. Outputs and logs must remain below the active `Lab/cases/<case-id>/` directory.
4. Capture WSL distribution/kernel and the tool's own version output.
5. If the command is missing, use `wsl-forensic-tooling`; do not substitute a different parser or installation method silently.
6. Before every command, expose in chat the exact command, its specific purpose, the meaning of every option and positional argument, inputs, outputs, expected side effects, and relevant stopping conditions. Redact secrets rather than placing them on a command line. If the command changes, disclose the revised command before execution.
7. Register the run-specific purpose and parameter explanation with the command before execution. A reusable method's generic purpose is not a substitute for the purpose of this invocation.
8. Capture stdout and stderr separately without hiding the exit status.
9. After every command, report in chat the exit status, relevant output, errors, limitations, and log or generated-file paths. Summarize rather than exposing secrets, excessive output, or unnecessary evidence content; do not present omitted output as absent.
10. Store the relevant-output summary, hash generated files, and complete the run record. Preserve failed runs and document retries as new runs.

Do not install packages, access the network, mount media, execute evidence content, or use destructive options without explicit authorization.
