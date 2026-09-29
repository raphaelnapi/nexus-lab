# Intake workflow

## Preconditions

- Create the case with `bash Lab/scripts/new-case.sh CASE-YYYY-NNNN` from the Nexus-Lab root inside WSL.
- Record who supplied the item, when and where it was received, its state, identifiers, and any physical or logical write protection.
- Prefer a hardware write blocker for physical media when appropriate. A WSL or Windows read-only flag is not equivalent to a hardware write blocker.

## Hash a regular evidence file

From the Nexus-Lab root in WSL:

```bash
python3 Lab/scripts/hash-evidence.py \
  --root "$PWD" \
  --evidence "$PWD/Evidence/CASE-YYYY-NNNN/item.E01" \
  --output "$PWD/Registry/CASE-YYYY-NNNN/item.hash.json"
```

The helper resolves paths, refuses sources outside `Evidence/`, refuses outputs outside `Registry/`, creates rather than overwrites the manifest, and checks size and modification time before and after hashing.

## Copy verification

Do not treat a normal file copy as forensic acquisition. Select a tool and method appropriate to the media and image format. Record the exact acquisition method. After copying, calculate hashes from the destination and compare them with the registered source or acquisition hash before analysis.

Do not mount an image merely to calculate its container hash. When mounting is authorized, use explicit read-only options and document the mount command and resulting mappings.
