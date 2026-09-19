# Literal PDF-error replay evidence

Producer: ZZ-SABLE-6D4F-R15 / GPT-6 Astra Pro. All inputs are fictional; execution occurred in an ephemeral Linux cloud container, not Bryce's machine.

`PDF_ERROR_EXECUTION.json.xz` contains the complete six stdout/stderr logs, their structured `results.json`, two replay-boundary checks, and the backend-absent test log. No logs are truncated in this archive. The initial interrupted run is not the source of these results.

- XZ bytes: 3,140; SHA-256 `7aba5284d4bfc87dd51df576bfb2fe4d8485b2de2d0f78eb899f61060d5839b8`.
- Decoded JSON bytes: 77,003; SHA-256 `f2c03d96332b969cfb9398906a5c52cee663b9810a67abdcb88842e8adad96de`.
- Git blob: `87c65e0f1789a142f9bb522344e0f86562750749`.
- Source before: `8b160a72a1e5c41c4372e7c9c207bc0d51d6157b`; after PDF-only repair: `efef6e5de841185b61bc11b11f5e41af5ee51d28`.
- Published suite: `1bd8f50021e87272cca136abe3a5f73ba15e90a8`; replay: `c912b9a2b0a17a4a19c156b9b69ca6d188e2c920`.

Read the archive without extracting or executing any file:

```python
import hashlib, json, lzma
from pathlib import Path
compressed = Path('PDF_ERROR_EXECUTION.json.xz').read_bytes()
if hashlib.sha256(compressed).hexdigest() != '7aba5284d4bfc87dd51df576bfb2fe4d8485b2de2d0f78eb899f61060d5839b8':
    raise ValueError('archive digest mismatch')
raw = lzma.decompress(compressed)
if hashlib.sha256(raw).hexdigest() != 'f2c03d96332b969cfb9398906a5c52cee663b9810a67abdcb88842e8adad96de':
    raise ValueError('decoded digest mismatch')
archive = json.loads(raw)
result = json.loads(archive['files']['current_replay/results.json'])
for run in result['records']:
    print(run['variant'], run['mode'], run['observed'])
```

Observed per mode (normal, actual optimized, ResourceWarning-strict): original 16 tests with6 failures/4 errors/zero skips; patched16/16 withzero skips. CPython3.13.5 and pypdf6.19.0. The supplied source was unchanged. Missing-backend execution is separately1 executed pass and15 skipped real-PDF methods; never a PDF pass.

These are focused PDF-error results, not full composed DOCX/TXT/fixture acceptance, hosted CI, or production-main integration. [The operator guide is on main](https://github.com/woahwhattheheck/commons/blob/main/revenue/uiowa_rfq_18649_document_extraction/PDF_DOCUMENT_ERRORS.md); its merge #16420 is distinct from canonical production PR #16309. Preserve current canonical source rather than copying an older complete extractor over it.
