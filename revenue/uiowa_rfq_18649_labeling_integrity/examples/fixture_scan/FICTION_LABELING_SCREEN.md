# Fiction-labeling screen

> This screen reports whether an artifact DISCLOSES that it is invented. It cannot tell whether the content is in fact synthetic, and it does not assert that any file contains a real University finding. Shape classification is heuristic. No lane is scored or marked compliant.

Scanned: `/home/user/fleet/staging/OP5-MARROW/revenue/uiowa_rfq_18649_labeling_integrity/fixtures`

- artifacts examined: **6**
- record-shaped artifacts missing a visible label: **2** across **2** lane(s)

| status | artifacts |
| --- | --- |
| `DISCLOSED` | 3 |
| `LABEL_BURIED` | 1 |
| `UNDISCLOSED_PROVENANCE` | 1 |
| `UNLABELED_CONFIG_SHAPED` | 1 |

`UNLABELED_CONFIG_SHAPED` is listed but is **not** a finding: schema, vocabulary and weight files present no records and need no fiction label. Counting them would overstate the problem.


## UNDISCLOSED_PROVENANCE - the finding

These carry assessment records or state results about the engagement's subjects, and the file says nowhere whether those contents are synthetic or real. A reader who opens one alone has no way to know. The remedy is a provenance statement, NOT necessarily a fiction label: a real measurement must not be labelled synthetic.

| lane | artifact | shape | why |
| --- | --- | --- | --- |
| `lane_records_unlabeled` | `findings.csv` | RECORDS | carries 3 record identifier(s) and 3 populated row(s) with assessment vocabulary; the file states nowhere whether its contents are synthetic or real |

## LABEL_BURIED - disclosed, but not where anyone will see it

A disclosure exists but sits past the opening of the file. Its own class rather than a pass: a reader is not protected by a note further down than they read.

| lane | artifact | shape | why |
| --- | --- | --- | --- |
| `lane_buried` | `report.md` | RECORDS | carries 25 record identifier(s) and 0 populated row(s) with assessment vocabulary; disclosure appears at byte 3813, past the first 1500 bytes a reader sees |

## Lanes with something to look at

| lane | artifacts needing a label |
| --- | --- |
| `lane_buried` | 1 |
| `lane_records_unlabeled` | 1 |

## Artifacts the screen could not read

None.

An unreadable artifact is never counted as labeled.

