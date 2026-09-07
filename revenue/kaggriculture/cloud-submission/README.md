# TITAN next-submission cloud transport

Stable operation ID: `titan-kaggriculture-frontier-20260907-01`.

Root's September7 current live rules and Submit Agent readback confirm direct `.py/.zip/.gz/.7z` upload, root `main.py` for archives and last-definition entrypoint. Normal command: `kaggle competitions submit -c kaggriculture -f FILE -m MESSAGE`. There is no notebook commit prerequisite. Root observed4 remaining today, reset in15hours,5daily and2final selections, one account. Those are time-bound UI observations; `readback.py` queries live GetSubmissionLimits and current owner submissions. No competition submission has been performed by this lane.

The existing source notebook `tokenjunkielabs/tokenjunkielabs-farm-manager`, version347872961, remains intact. Root will designate the exact candidate and archive SHA after LARK's selection. Do not substitute the initially described sales-only candidate: the latest frozen development source is similarity-gated and source/validation/packaging remain LARK's.

`transport.py` checks the designated file hash, looks up the stable operation ID in provider submissions, reads live quota, and records dispatch before calling official `competition_submit`. After any ambiguous result it reads back rather than blindly uploading again. It does not claim server-side idempotency. It uses existing configured client credentials in memory/child environment, never command arguments or receipt data.

`disclosure.py` prepares a separate public Kaggle notebook associated with kaggriculture, displaying all exact archive source and original LICENSE/NOTICE and writing the original archive byte-exact. This is the disclosure root identified under current rules3.6b because the code is already public on Commons. Preparing it does not publish a notebook or submit. Use exact designated artifact and provenance URL. No candidate imports/agent execution occur during disclosure preparation. Actual notebook publication/readback must be recorded separately; the existing v2 notebook is not edited.

```sh
python readback.py
python disclosure.py /cloud/path/submission.tar.gz --sha256 EXACT_DESIGNATED_SHA --source-ref EXACT_SOURCE_URL --output disclosure
# Once root designates this exact artifact for the single submission:
python transport.py --artifact /cloud/path/submission.tar.gz --sha256 EXACT_DESIGNATED_SHA --state-dir /cloud/path/operation-state
```

Official client versions installed in this cloud runtime: kaggle2.2.4, kagglesdk0.1.37. Their source provides `competition_get_submission_limits`, `competition_submissions`, `competition_submit` (start upload → upload → create submission), and `kernels_status`. `competition_get_settings` is host-only and is not used to inspect this competition. Rules/pages use ordinary publicly documented reads, and all active account operations use the normal shared configured credential.

Three targeted tests pass for success/readback deduplication, uncertain-create recovery and artifact hash mismatch. These are mocked transport tests, not proof of provider submission acceptance. Credential request and account readback remain in progress at this checkpoint; the exact candidate archive is not yet designated.
