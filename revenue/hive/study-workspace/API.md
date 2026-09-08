# Hive Study document and review API

Contribution: ASTRA-CEDAR. Consumer: ASTRA-FOLIO's browser workspace for demand
`bm-hive-20260908-002`. One canonical product directory:
`revenue/hive/study-workspace/`.

## Runtime

Python 3.10 or newer, standard library only. Text-PDF extraction uses an installed
Poppler `pdftotext` executable, without network calls. Text and Markdown import
remain available without Poppler. No OCR, external model, telemetry, paid service,
or school/grading integration is used. Scanned PDFs require a transcription.

`python app.py --data /path/outside/source/workspace.sqlite3 --port 8768`

The server serves `index.html`, `workspace.js`, and `style.css` beside `app.py`.
FOLIO owns the integrated browser assets and browser acceptance. This backend
contribution alone is not the complete delivered browser product.

The default listener is loopback. This is one shared workspace: everyone who can
reach the server can read, edit, export, or delete its content. It does not separate
student accounts or provide confidential multi-tenant hosting. Deploy only in an
environment appropriate for the material. Original files, text, keys, submitted
answers, and review state are stored in the SQLite database. Browser consumers
should keep only the selected document and a pending review payload in their
local/session storage, and remove those references on deletion. Deletion removes
active rows, not exported copies, backups, or a guarantee of disk sanitization.

## Endpoints

All request bodies are JSON objects. All responses are JSON except static files,
the source view, and the original-file download. Responses use `no-store`.

| Method and route | Request / response |
| --- | --- |
| `GET /api/capabilities` | `{pdf, max_upload, generation}`. `pdf` reports installed converter availability. |
| `GET /api/documents` | `{documents:[{id,title,filename,kind,created_at,cards,due,attempts}]}` |
| `POST /api/import` | `{filename,title?,data}` where `data` is base64 original bytes. Returns `{id,cards,duplicate,notice?}`. |
| `GET /api/documents/{id}` | `{id,title,filename,kind,pages:string[],created_at}` |
| `GET /api/documents/{id}/cards` | `{cards:[card]}`; add `?due=1` for due cards only. |
| `POST /api/cards/{id}` | `{prompt,answer,aliases:string[],explanation,revision}`. Returns the updated card. |
| `POST /api/review` | `{card_id,answer,request_id,revision}`. Returns the durable review result below. |
| `GET /api/documents/{id}/export` | Downloads `hive-study-export-v1` JSON with source text, cards and reviews. |
| `DELETE /api/documents/{id}` | Removes the document and its cards/reviews; repeated deletion is harmless. |
| `GET /source/{id}#pN-lN` | Escaped original extracted text with stable one-based page/line anchors. |
| `GET /original/{id}` | Downloads the exact original bytes. |

A card includes `id`, `document_id`, `prompt`, `answer`, `aliases`, `kind`, `page`,
`line_start`, `line_end`, `quote`, `explanation`, `revision`, `due_at`,
`interval_days`, `repetitions`, `lapses`, `attempts`, and `source_url`.

`kind` is `definition` or `cloze`. Prompts are derived using inspectable rules,
not generated factual explanations. The tutor may edit an explanation. Quotes
remain exact extracted source lines. PDF references identify extracted text
pages/lines, not a guessed printed page label or bounding-box annotation.

A review returns `card_id`, `correct`, `answer`, `submitted`, `explanation`, `quote`,
`source_url`, `page`, `line_start`, `revision`, `due_at`, `interval_days`,
`request_id`, and `feedback`. All times are Unix seconds. A correct normalized
key/alias match schedules 1 day, then 3 days, then doubled intervals capped at
180 days. A mismatch schedules 10 minutes and restarts the correct-answer streak.
This is a simple review schedule, not a measured learning-outcome claim. Matching
normalizes Unicode, case and word punctuation; it is not semantic grading.

## Consumer invariants

Generate a fresh `request_id` for each intended answer. Persist the entire pending
payload before sending. On a lost response, resend the exact same payload and ID;
the atomic SQLite transaction returns its original result without adding another
attempt. Reusing that ID with a different answer, card, or revision returns 409.
Keep the payload until the server responds; do not silently assign a new ID after
a network interruption. Reload the full due queue when resuming so recovering one
review does not discard another due card.

Edits require the displayed `revision`. An intervening edit or a stale answer
returns 409; reload the key before continuing. A key edit increments the revision,
reschedules that card immediately, and preserves all previous reviews.

The document ID is the original bytes' SHA-256. Reimporting identical bytes keeps
all keys/progress and the original title, even when the incoming filename differs.
Changed bytes create another document; do not describe this as automatic version
merging. Empty or non-readable sources return 400. A readable source with no usable
practice lines is saved with an explicit zero-card notice. At most 80 cards are
derived per document. Source files are limited to 8 MiB and extracted text to two
million characters. Export includes text and progress; original binary files are
obtained separately from `/original/{id}`. An import/restore operation for an
export snapshot is not implemented by this version.

Input errors use 400 with `{message}`; missing objects/routes use 404; concurrent
revision or operation conflicts use 409; storage errors use 503. The HTTP consumer
must surface these messages and preserve pending data for transient failures.

## Tests

From this directory: `python -B -m unittest -v test_study`.

The 29 tests exercise actual temporary SQLite databases, concurrent imports and
reviews, original-byte hashes, citations, editable keys, schedule boundaries,
reopen/retry behavior, exports, deletion, and a real local HTTP server. When
`pdftotext` is installed, a generated two-page original PDF goes through the real
converter and HTTP import. PDF tests report a skip explicitly when it is absent.
No user document is committed as a fixture. Browser acceptance belongs to the
composed product and is reported separately.
