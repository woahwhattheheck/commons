# Preserve bracketed IPv6 links in the inbox relay

Operation: `newline-resume-inbox-ipv6-20260908-01`. This composes ASTRA-RELAY's saved `astra-relay-ipv6-tokenization-20260908-01` repair with the current readable-MIME implementation. ASTRA-VISIBILITY, MAIL, charset, URL, alternative and COOLDOWN authorship remains intact.

## Behavior and scope

The former URL token ended at the closing bracket of a valid IPv6 authority. It fed an incomplete address into the existing parser and left the remainder of the URL in the work message. The replacement token keeps the complete bracketed authority, port, path, query and fragment together. The existing parser and secret/query/action-link handling remain unchanged. Generated `[REDACTED]` text is kept inside its URL token, while surrounding prose or Markdown brackets still terminate ordinary links.

Only the URL assignment and its comments change in `host/inbox_slack_relay.py`. All other production ASTs match current worker `6a6b7a669ee766370a0458f4df204bb641871654`, including the newer readable-MIME correction from commit `48f0b37f1e50831604973d8c1146b9746beb0711`. No provider, scheduler, source-routing, credential, deduplication or activation behavior changes.

The URL test file is ASTRA-RELAY's exact prepared `ed0d83d668a1b6cee7ad9f6c258407a6031d4476`: 18 existing methods preserved plus 26 IPv6/token cases. No new test framework or workflow is introduced; the existing inbox regression command already includes this file.

## Executed current-source composition

Base main: `cc428ca5e45f011dc6f070f722929cb55c3e409a`.
Current worker: `6a6b7a669ee766370a0458f4df204bb641871654`.
Composed worker: `ca52516e2ff5e2f51232d64570ff0e3a2bb5ceed`, SHA256 `acaa81b04e00b0988fc53c4da4df23da7a48cca72ebed881346c8889df2a60b9`.

Python 3.13.5 in the existing isolated cloud container:

- The complete 44-method URL module passes, zero failures or errors, on the composed source. Its exact current predecessor has 23 assertion failures and zero errors.
- Four additional synthetic messages exercise the newer readable-MIME fallback through actual `gmail_events` and `Event.messages`: attachment-only or malformed plain parts followed by readable plain/HTML IPv6 content, including a sensitive query. All four retain the available work body, report no pending body, preserve caller inputs and use only the three expected recording-provider reads. No real network or mailbox call occurs.
- All production AST outside the single URL assignment is identical to current main. Uploaded source and test blobs match the executed files.
- The initial test invocation was from the parent directory and produced a module-import error before any product test ran; that log is retained separately. Correct-directory executions above are the actual product results.

Reproduction from repository root:

```sh
python3 -B -m unittest -v test_inbox_slack_relay_urls
```

## Original and composed evidence

The original saved repair is `astra-relay-ipv6-repair-20260908.zip`, Library file `file_00000000de0481f7b8bc38b3d9f60b13`, 58051B, SHA256 `c67b4186c3d9db828611204b793021bb40a4d1af125b8d4c112ae18a1c10c023`. All 16 payloads were verified. Its earlier 44-method execution and mutation results retain their original source identity; they are not extra new tests.

The new current-MIME composition, complete before/after logs, four-case executable join, and exact source snapshots are saved in `INBOX_IPv6_MIME_COMPOSITION_20260908.zip`, Library file `file_00000000037081f594794c6fc6a78ab8`, 41092B, SHA256 `977e3800ec9733ebb5d0c99eeef892de083f1bd3b836022eab94b2a0708ab44d`. All 11 payloads are manifested. The original package is not duplicated.

These are local parser/provider-fixture results, not real inbox delivery or service activation. No live source message, account, scheduler, Slack forwarding or owner-PC action was performed. F/equipment retains the existing activation work. Broader hosted and repository checks must retain their own source-specific results.
