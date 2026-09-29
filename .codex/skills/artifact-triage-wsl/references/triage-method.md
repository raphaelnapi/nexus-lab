# Bounded triage method

Select tools by evidence type rather than running every available parser.

Suggested stages for disk images:

1. Identify container and image segments with format-aware, read-only inspection.
2. Inventory partitions and offsets, for example with Sleuth Kit `mmls`.
3. Inspect filesystem metadata with format-aware tools such as `fsstat` and `fls`.
4. Extract a justified subset with tools that write only to the case output directory.
5. Record encrypted, damaged, unsupported, hidden, slack, and unallocated areas separately.

For logical collections, inventory file type, size, hashes, timestamps, permissions, extended attributes, alternate streams where applicable, and archive/container relationships.

Do not rely only on filename extensions. Do not mount a filesystem when a read-only parser can answer the question. If mounting is necessary, obtain authorization and document the read-only mapping, offset, filesystem driver, and unmount result.
