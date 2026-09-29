# Timeline method

Store raw and normalized timestamps together. A timeline row should include:

- event ID and case ID;
- original timestamp string and semantic meaning;
- source timezone or `unknown`;
- normalized UTC timestamp, when justified;
- resolution and uncertainty;
- evidence ID, artifact ID, source locator, parser, and tool-run ID;
- event description and interpretation status.

For tools such as Plaso `log2timeline.py` and `psort.py`, record version, parser selection, timezone settings, filters, command line, storage-file hash, export hash, warnings, and rejected inputs. Write Plaso storage and exports only below `04-timelines/`.

Validate important events against the underlying artifact or a second independent method. Parser-generated timestamps are observations about parser output until corroborated with their source semantics.
