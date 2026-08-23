# ASTER BRIDGE — open-link connection guide

The tracked ASTER bridge exposes its existing local adapter operations on a
loopback link. Possessing that link is sufficient caller access. The bridge
does not mint, read, compare, or request a credential, and it does not turn
callers away when request volume rises.

The public caller boundary and the outbound integrity boundary are separate:

- caller action names, parameter names, parameter shapes, and text content are
  admitted without a policy screen;
- known adapter operations keep their established defaults and behavior;
- adapter results must still satisfy their declared result shape before they
  cross the bridge;
- the append-only local audit and opaque action receipts remain intact.

## Link and request

Start the bridge:

```powershell
python aster_bridge.py --port 7891
```

Call it without a credential header:

```http
POST http://127.0.0.1:7891/rpc
Content-Type: application/json

{"action":"status","params":{}}
```

`verb` remains an accepted alias for `action`, so existing callers continue to
work:

```json
{"verb":"home.write","params":{"text":"any caller text","extension":true}}
```

`params` may contain extra fields or may be a non-object JSON value. For a
known operation, documented optional defaults are filled to preserve existing
adapter behavior. Nothing else is removed or screened before dispatch.

The other open routes are:

```text
GET /manifest
GET /health
```

The listener remains on `127.0.0.1`. This is a local-link property, not caller
identity or permission handling.

## Responses

Known-operation success:

```json
{"ok":true,"verb":"status","ts":"2026-08-23T12:00:00Z","data":{"live":true}}
```

Errors contain constant codes and never serialize local exception text:

```json
{"ok":false,"verb":null,"ts":"2026-08-23T12:00:01Z","error":{"code":"E_STATE","message":"resource not available"}}
```

Transport parsing still rejects malformed JSON and bodies above the transport
ceiling. That is byte-stream integrity, not action or parameter admission.

| Code | Meaning |
| --- | --- |
| `E_METHOD` | unsupported HTTP request |
| `E_PARAM` | malformed request framing or JSON |
| `E_SANITIZE` | result could not satisfy the outbound contract |
| `E_STATE` | referenced resource or executable route is unavailable |
| `E_INTERNAL` | operation failed; diagnostic detail stayed local |

## Known adapter operations

This table is discovery and compatibility documentation. It is not caller
admission policy.

| Action | Advisory params | Result |
| --- | --- | --- |
| `status` | none | live summary |
| `players.list` | none | participant handles |
| `players.message` | `to`, `body` | delivery count and receipt |
| `surface.state` | none | surface dimensions and generation |
| `home.read` | `limit` | durable entries |
| `home.write` | `text` | entry receipt fields |
| `scratch.read` | `limit` | ephemeral entries |
| `scratch.write` | `text` | entry receipt fields |
| `task.submit` | `objective`, `detail` | task handle and state |
| `task.observe` | `task` | task progress |
| `optimize.list` | none | opaque capability handles |
| `optimize.request` | `capability`, `objective`, `bound` | acceptance receipt and generation |
| `receipt.get` | `receipt` | receipt outcome and generation |

The diagnostic fields `probe_fault`, `probe_taint`, and `probe_undeclared`
remain available on known operations. They exercise the outbound integrity
path and return only constant errors.

## Other action strings

The tracked build contains no stable Python-callable or deployed local
Action-Pad/fire-action route that this bridge can reuse. Therefore an action
without an existing adapter reaches dispatch and returns `503 / E_STATE`
(`route unavailable` in the host-only audit), not the former unlisted-action
error.

The bridge does not import `action_executor.py`, spawn a command interpreter,
embed the candidate Door server, or depend on concurrent unstaged code. Doing
any of those would create a new shell/RCE or deployment mechanism rather than
reuse an available route. If a stable explicit action road is later present,
it can be connected as a separately reviewed adapter while keeping its receipt
opaque at this boundary.

## Outbound integrity and receipts

Caller text is not scanned on entry. Result data is still reconstructed from
the declared output shape, checked for undeclared fields and local diagnostic
leakage, and scanned once more after JSON serialization. A result that cannot
be proven returns `E_SANITIZE`; the adapter call and its local audit entry are
not rewritten.

This means a caller can write arbitrary text successfully even when a later
read would be withheld by the outbound IP boundary. That is an output contract,
not a caller lock.

Existing receipt behavior is unchanged:

- `players.message` and `optimize.request` return opaque `rc_…` handles;
- `receipt.get` returns the recorded action, outcome, and configuration
  generation for a known receipt;
- the append-only host audit is flushed on every call and is never served.

## Generated manifests

Regenerate both checked-in manifests after an interface change:

```powershell
python aster_bridge.py --emit-manifest --emit-openai
```

`ASTER_TOOL_MANIFEST.json` describes open-link access, advisory known-operation
parameters, and the absence of a tracked fallback route.

`ASTER_OPENAI_TOOLS.json` contains:

- `aster_action`, a generic open action/params request shape;
- compatibility shortcuts for every known adapter operation.

All function parameter schemas permit extra fields and require none. The
adapter may still need particular values to complete a particular operation;
that is operation behavior, not admission at the bridge.

## Files and verification

| File | Purpose |
| --- | --- |
| `aster_bridge.py` | open HTTP dispatch, adapter join, outbound final check, manifest emitters |
| `public_schema.py` | known-operation discovery, advisory defaults, outbound result contracts |
| `private_adapter.py` | existing operations, opaque handles, receipts, audit |
| `denylist.txt` | outbound-only vocabulary policy |
| `ASTER_TOOL_MANIFEST.json` | served public manifest |
| `ASTER_OPENAI_TOOLS.json` | generic action tool plus known-operation shortcuts |
| `test_leakage.py` | real-socket open-access and outbound-integrity sweep |

Focused verification:

```powershell
python -m py_compile aster_bridge.py public_schema.py private_adapter.py test_leakage.py
python test_leakage.py
```

