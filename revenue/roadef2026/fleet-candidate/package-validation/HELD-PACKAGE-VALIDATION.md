# S139 frozen qualification context — held package validation

Candidate **`S139-fleet-20260908-75897709`** remains frozen at commit
`6feb9c0566b8f203c5d1a2ffdfbf1cb6d11be055`. This package is private build and
review material. It has not replaced the existing Gmail attachment and has not
been submitted.

## Exact context

- Held context ZIP: `ROADEF-S139-held-qualification-context-20260908.zip`
- ZIP: 1,800,567 bytes; SHA-256 `659b3ac1dcd6e1dc63c8ef6ab4acf306740b3d9334b4b29691c479833fcb5df3`
- Archive inventory: 319 files; 318 manifest rows; zero mismatches
- Verified upstream transfer: 336/336 rows from existing QUARTZ context `62bb113f6fecf074fad8a5a76623c548d099466e230f509c8e353fb2b2e181e6`
- Rebuilt source manifest: 317/317 files; zero problems; all four dependency archive pins retained
- Candidate source: exact base `322ec2e6…` plus exact patch blob `0ff8d2ee…` gives 37,251-byte SHA-256 `758977095f8f34263bbcd9ed043ac4ab7943f04f65fae530c78ee64787c34f8f`
- Runtime binds supervisor blob `6a32f242…`, checker reader `6d6812e1…`, and preparer `88814648…`

## Native build and interface validation

The context's unchanged `sh build.sh` completed with exit 0 in **0:40.00**, using
99% CPU and peak RSS **794,176 KiB** under
`g++ (Debian 14.2.0-19) 14.2.0`. It produced all four expected ELF binaries:

| Binary | Bytes | SHA-256 | No-argument result |
|---|---:|---|---:|
| candidate | 151,400 | `b4051304e3762eaf0aa8d2ef595fbc0c295f459345c5d2d62cab771343091126` | 2 |
| SEDGE | 124,464 | `6425ae47e2686dafae1ad16ca1d08c2a168e9ed0dd581590ec9faa8d17035622` | 2 |
| FLORA | 133,592 | `f59b3e128ea7d678b38d5e0bfd2ca23842ab24dba2fbb7f9fe267f5f449141d5` | 2 |
| official checker | 1,271,728 | `e2a2297b5a43aaf4d95d6cbc65b16e62d4fc5fb1381e59a2323a8bad3015a472` | 255 |

`run.sh` returns 2 with its four-argument usage line when called without inputs. No
solver/checker instance, public benchmark, or Docker container was executed in this
validation.

## Method description

The package includes the validated two-page A4 `method.pdf`, 7,596 bytes, SHA-256
`4ece1ee204ef33b93b76cdeb009733dabc67c69783fb6dc5bbe845ab62c90502`.
Both pages passed visual inspection. Normalized extracted text matches all 5,726
visible source characters; 769 words were found, with zero word boxes outside page
bounds. The PDF is openable, unencrypted, nonscanned, and has no XFA, forms, or
attachments. Two source links are present.

## Held artifacts

- Context ZIP: Library `file_00000000336481f5ab32478b3c67ba57`, 1,800,567 bytes, SHA-256 `659b3ac1dcd6e1dc63c8ef6ab4acf306740b3d9334b4b29691c479833fcb5df3`.
- Complete evidence ZIP: Library `file_0000000015dc81f58582fe42c9829d38`, 1,768,455 bytes, SHA-256 `aaddbe6956988847bde95f2ff65484e0004c22d771ca7f71c151d6b4fd0e3b79`.
- PDF: Library `file_00000000d61881f5aa1a5aff234ce8af`.

## Limits and hold

This establishes exact source assembly, inventory, local native buildability, basic
four-argument interface shape, and method-document readiness. The native compiler
was Debian GCC 14.2, not the organizer's final Ubuntu 24.04 image. RENEW retains the
actual Docker lane; QUARTZ, LANDING, and LARCH retain frozen public-B validation.
The existing Gmail draft and attachment were not opened, changed, or sent. No
organizer contact or qualification submission occurred.
