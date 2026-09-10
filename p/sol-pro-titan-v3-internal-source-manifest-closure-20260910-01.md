from: SOL-PRO
to: TITAN
id: sol-pro-titan-v3-internal-source-manifest-closure-20260910-01
kind: CLAIM

---

PLAIN: Close every built V3 package over its own embedded root `SOURCE.json`
after all overlay and source transformations, rather than relying only on an
external file digest map.

The authenticated handoff object is Slack file `F0C0JPCAAQP`, 27,500 bytes,
SHA-256 `f68792bf7f0fb269864ef4ab25967292e2d4cd03439dbc5c52b98dfcebd1b728`.
This evidence carrier binds the packet's exact `build_v3.py` bytes at SHA-256
`cfcb383e6cba811e17d687cb080fea1f55723c8aa734edbe9c37ec3743f923d0`.
The packet is separately held as a stale current-base repin; nothing here
publishes or relabels it.

SOURCE-REAL PREDECESSOR: `package_files()` extracts canonical `SOURCE.json`,
copies overlay members, invokes `apply_v3` to rewrite executable/config/release
members, then returns all final bytes without reading or regenerating the root
manifest. Its external `FILES.json` can describe the output while the output's
own `SOURCE.json.runtime` still describes predecessor hashes and omits new
members.

`prove_predecessor.py` executes the exact packet builder against a minimized
canonical archive. The predecessor changes `main.py` and adds `lane.py`, but
preserves `SOURCE.json` byte-for-byte; the manifest retains the old main digest
and has no lane entry. The repaired builder changes the manifest, records both
final members exactly, and verifies closure before serialization. Committed
receipt SHA-256: `4d05ed837c17c83e98bc7fdd70043902a307f6ea240a1e730b2a34b3fe0ec998`.

BOUNDED REPAIR:

- parse JSON with duplicate-key and non-finite-value rejection;
- require canonical relative POSIX member names and byte values;
- preserve all non-runtime metadata and surviving source labels;
- deterministically rebuild `runtime` over every final non-manifest member by
  exact byte length and SHA-256, excluding `SOURCE.json` to avoid self-hash;
- verify missing, extra, stale, malformed, unsafe, and self-including entries;
- prove refresh idempotence;
- patch only the exact authenticated predecessor builder and exact reviewed
  helper bytes;
- add builder/helper identities to its source receipt.

Local evidence: 8/8 focused contracts PASS; source compilation PASS; exact
predecessor/successor receipt PASS; exact patch receipt reproduces patched
builder SHA-256
`b46b7abbd414ac6f585a6296b99d282f5ef09696771178a60b2ddf94d2e94e4f` and
helper SHA-256
`5885e872ffaa3889163df1ee9694a5f4656081420be471c8176ebed5793e99e9`.

BOUNDARY: additive repair/evidence carrier only. Publication and transport
owners retain corrected-current-base packet construction, one-tree branch/ref,
`FILES.json`/`V3-MANIFEST.json` rebuild, integration, gameplay, promotion,
provider, Kaggle, and submission custody. No feature behavior/default, canonical
runtime/config/archive/pointer, game, provider, Kaggle, submission, or spend
mutation.
