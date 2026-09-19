# Capability appendix - evidence index

Verbatim output and file digests behind each capability in the appendix. Digests are of the exact bytes that were executed.

## BAD-01 - language: marketing adjective

**Status:** NOT DEMONSTRATED

- Blocker: wording rejected (marketing language: 'seamlessly'; marketing language: 'robust')

**Contributing seat:** fixture

**Reported commit:** `not recorded` - status not recorded

**Working directory:** `.`

**Command:** `python3 capability_appendix.py`

**Observed output (verbatim, exit 0, 2026-09-19):**

```
usage shown
```

**Artifact digests:**

| File | Digest at demonstration |
|---|---|
| `capability_appendix.py` | not recorded |

## BAD-02 - language: certification and guarantee

**Status:** NOT DEMONSTRATED

- Blocker: wording rejected (prohibited certification or guarantee language: 'certified'; prohibited certification or guarantee language: 'compliant'; prohibited certification or guarantee language: 'guaranteed')

**Contributing seat:** fixture

**Reported commit:** `not recorded` - status not recorded

**Working directory:** `.`

**Command:** `python3 capability_appendix.py`

**Observed output (verbatim, exit 0, 2026-09-19):**

```
usage shown
```

**Artifact digests:**

| File | Digest at demonstration |
|---|---|
| `capability_appendix.py` | not recorded |

## BAD-03 - binding: missing artifact

**Status:** NOT DEMONSTRATED

- Blocker: artifact file(s) not found: tool_that_does_not_exist.py

**Contributing seat:** fixture

**Reported commit:** `not recorded` - status not recorded

**Working directory:** `.`

**Command:** `python3 capability_appendix.py`

**Observed output (verbatim, exit 0, 2026-09-19):**

```
usage shown
```

**Artifact digests:**

| File | Digest at demonstration |
|---|---|
| `capability_appendix.py` | not recorded |
| `tool_that_does_not_exist.py` | not recorded |

## BAD-04 - binding: no observed run

**Status:** NOT DEMONSTRATED

- Blocker: no observed run recorded for this claim

**Contributing seat:** fixture

**Reported commit:** `not recorded` - status not recorded

**Working directory:** `.`

**Command:** `python3 capability_appendix.py`

**Artifact digests:**

| File | Digest at demonstration |
|---|---|
| `capability_appendix.py` | not recorded |

## BAD-05 - binding: demonstration failed

**Status:** NOT DEMONSTRATED

- Blocker: demonstration exited 2

**Contributing seat:** fixture

**Reported commit:** `not recorded` - status not recorded

**Working directory:** `.`

**Command:** `python3 capability_appendix.py`

**Observed output (verbatim, exit 2, 2026-09-19):**

```
error: cannot read claim register
```

**Artifact digests:**

| File | Digest at demonstration |
|---|---|
| `capability_appendix.py` | not recorded |

## BAD-06 - binding: artifact changed after demonstration

**Status:** NOT DEMONSTRATED

- Blocker: artifact changed since it was demonstrated: capability_appendix.py. The recorded run no longer describes these bytes.

**Contributing seat:** fixture

**Reported commit:** `not recorded` - status not recorded

**Working directory:** `.`

**Command:** `python3 capability_appendix.py`

**Observed output (verbatim, exit 0, 2026-09-19):**

```
usage shown
```

**Artifact digests:**

| File | Digest at demonstration |
|---|---|
| `capability_appendix.py` | sha256:0000000000000000000000000000000000000000000000000000000000000000 |

## BAD-07 - binding: instruction points elsewhere

**Status:** NOT DEMONSTRATED

- Blocker: demonstration command invokes some_other_script.py, which the claim does not cite

**Contributing seat:** fixture

**Reported commit:** `not recorded` - status not recorded

**Working directory:** `.`

**Command:** `python3 some_other_script.py`

**Observed output (verbatim, exit 0, 2026-09-19):**

```
usage shown
```

**Artifact digests:**

| File | Digest at demonstration |
|---|---|
| `capability_appendix.py` | not recorded |

