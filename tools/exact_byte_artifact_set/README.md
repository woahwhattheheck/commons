# Exact-byte artifact-set publisher

`tools.exact_byte_artifact_set` is a small, zero-dependency filesystem-custody primitive for commands that need to publish several exact byte strings into one already-existing output directory.

It exists because three checks answer three different questions:

- **pathname identity**: what object does this name resolve to *now*?
- **inode identity**: is the visible name still the same filesystem object the invocation created?
- **exact retained bytes**: does the invocation's retained readable descriptor still contain the exact bytes it intended to publish?

Checking only the first two is insufficient. A same-inode, same-length in-place rewrite can keep `(dev, ino, size)` unchanged while corrupting the artifact bytes. This publisher retains readable file descriptors for the whole set and verifies exact bytes from those same descriptors before reporting success.

## Contract

`publish_artifact_set(output_dir, artifacts)`:

1. walks and opens the existing directory with descriptor-relative `O_DIRECTORY|O_NOFOLLOW` custody;
2. preflights the complete requested leaf set before creating any output;
3. creates every leaf `O_EXCL|O_RDWR|O_NOFOLLOW`, drains short writes, and retains all leaf descriptors;
4. fsyncs files and the retained directory;
5. verifies exact expected bytes from each retained descriptor with stable metadata;
6. proves each visible leaf still names that retained regular-file generation;
7. repeats the final byte/visibility fence, fsyncs the directory again, and returns a deterministic SHA-256 receipt.

If publication has begun and any later check fails, **nothing is pathname-deleted**. `PartialPublicationError.created_leaves` reports the invocation-created names so the caller can reconcile the partial truth. This is deliberate: a late cleanup that re-resolves a pathname can delete another actor's replacement.

The primitive is intentionally conservative: safe single-component names only, existing leaves are refused, the output directory must already exist, payload sizes are bounded, and platforms without the required POSIX descriptor primitives fail closed.

## Example

```python
from tools.exact_byte_artifact_set import publish_artifact_set

receipt = publish_artifact_set(
    "build/output",
    {
        "packet.json": b'{"state":"HOLD"}\n',
        "packet.md": b"# Packet\n\nHOLD\n",
    },
)
assert receipt["publication_complete"] is True
```

The receipt contains only sorted leaf names, byte lengths, SHA-256 digests, and the set digest. It never contains the output path or artifact contents.

## Non-authority

This utility proves a bounded filesystem publication property only. It does not prove that artifact semantics are correct, that evidence is authentic/current, that a buyer accepted anything, or that an external send/payment/deployment is authorized. Product-level authority gates remain separate.
