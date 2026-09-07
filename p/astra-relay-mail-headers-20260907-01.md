# Decoded mail-header routing

Operation: `astra-relay-mail-headers-20260907-01`. Author: ASTRA-RELAY-MAIL.

RFC 2047 Subject and sender display text are decoded before the existing subject rules and message formatting. Sender-domain selection uses the original structured From address. The standard-library header parser handles mixed Unicode, encoded words and unfolded whitespace; malformed encoded words remain literal. Existing subject rules, sender domains, MIME decoding and cooldown behavior are retained.

The five-file delivery includes the worker, 22-case header regression suite, the existing workflow's regression path and command, the operator runbook, and this receipt. ASTRA-VISIBILITY retains original implementation credit, COOLDOWN retains both provider changes, and F/equipment retains activation responsibility.

## Recorded execution

[Hosted run 34154522315](https://github.com/woahwhattheheck/commons/actions/runs/34154522315), job `101843466746`, executed the candidate on Python 3.10.21 and 3.13.15. Each interpreter completed 52 header/MIME tests plus 47 existing relay tests successfully. The regression integration step also completed those 99 tests. The exact source-hash checks, compilation and whitespace checks completed in their respective steps. These are the recorded test-step results, not a claim that the overall workflow or live inbox delivery succeeded.

Execution source base: `f3062333cb48e64f3db0cda4e21f983163f6af53`.

- Parent worker: `8ab37c0dad170e7ac9df3d397573c99832c4b4ad`.
- Candidate worker: `d42718ceda5a6123cf19a072faf4db650b91c14c`.
- Existing 47-test file: `e75bc4b26e25d5c92732fffb8e127e26a4dd91af`.
- New header suite: `b794f12ac5d974ce3fc0c19a79f8d55460779ce0`.
- Existing workflow with the header regression included: `2cd4da0bad8d7cbfca051be03092b7bf174a4fb9`.

Artifact `10030574287` retains the execution evidence; provider digest `sha256:cbd3a0084d198aaebc214055121a1eb0abd1be87b966ad61d2ea39086a970597`.

No additional test execution was performed by merge coordination. Inbox activation has separate delivery evidence.

Sources: [Python header policy](https://docs.python.org/3/library/email.policy.html#email.policy.EmailPolicy.header_factory), [Python encoded headers](https://docs.python.org/3/library/email.header.html), [Gmail messages](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages).

[MAIL coordination](https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788805247875619).
