# Methodological mapping

## ISO/IEC 27032:2023

Use this standard as the cybersecurity and Internet-security context for Nexus-Lab:

- identify stakeholders, authority, roles, communication paths, and responsibilities;
- constrain network exposure and external sharing;
- protect the WSL host, laboratory accounts, tools, case records, and sensitive outputs;
- document dependencies between host security, network security, web security, and the examination environment;
- obtain authorization for network access, external services, or sharing case data.

## ISO/IEC 27042:2015

Use this standard as the primary analytical and interpretive frame:

- **continuity:** trace each result to a registered evidence item and every transformation;
- **validity:** justify that the selected method is fit for purpose and note validation evidence;
- **repeatability:** preserve enough detail for the same examiner, environment, and method to repeat the result;
- **reproducibility:** preserve enough detail for another competent examiner to evaluate the result independently;
- **interpretation:** distinguish what the artifact states from what the examiner infers;
- **competence and scrutiny:** expose assumptions, limitations, deviations, and review status.

## Required examination record

Record the question, scope, evidence identifiers and hashes, environment, method, tool and version, exact command, parameters, start/end UTC times, output hashes, errors, deviations, observations, interpretations, alternative explanations, confidence, and reviewer.

## Epistemic states

Assign each material statement one of these states and preserve its source:

- **reported:** supplied by a person or external record and attributed to that source, but not independently verified;
- **observed:** directly present in a registered record or produced by a documented examination of verified evidence, with an evidence ID, locator, and tool run where applicable;
- **derived:** deterministically calculated or transformed from cited inputs, with the formula, query, script, or transformation preserved;
- **inferred:** an analytical interpretation supported by cited observations, with assumptions, alternatives, limitations, and confidence stated;
- **concluded:** an answer to the examination question supported by the preceding states and bounded by scope and limitations;
- **unknown:** the value is unavailable or has not been supplied;
- **not observed:** a defined, successfully executed method did not detect the item within its documented coverage;
- **not determined:** the available evidence, method, access, or validation is insufficient to decide.

Do not promote `reported`, `derived`, `inferred`, `unknown`, `not observed`, or `not determined` information into a direct observation. A parser result is an observation of parser output until checked against the source semantics. A negative finding is valid only within the method's recorded scope, coverage, successful execution, and limitations.

Model knowledge can support method selection and interpretation but cannot supply case facts. Do not fabricate missing fields, expected values, commands, outputs, hashes, timestamps, identities, provenance, or citations. If a required fact cannot be obtained from a registered source or an authorized tool run, preserve the gap explicitly.

Official references:

- https://www.iso.org/standard/76070.html
- https://www.iso.org/standard/44406.html

These public summaries do not replace licensed copies of the standards or a formal conformity assessment.
