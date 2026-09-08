from pathlib import Path

path = Path("board_ingest.py")
text = path.read_text(encoding="utf-8")
if "def _classify_bounded_bake_reset(" in text:
    raise SystemExit("classifier already exists")

marker = "\ndef _record_paths(env):\n"
if text.count(marker) != 1:
    raise SystemExit(f"unexpected record-path marker count: {text.count(marker)}")

helper = r'''def _classify_bounded_bake_reset(env, recorded):
    """Classify a second bake replay reset without making a third push.

    The refreshed origin is acceptable only when it already carries an exact
    receipt for the current source corpus: either the projection converged or
    the durable pending marker schedules the ordinary heal. A stale checkout
    without either source-bound receipt remains a failure.
    """
    source = post_source_snapshot()
    converged_rel = _projection_receipt_rel(source["sha256"], "converged")
    pending_rel = _projection_receipt_rel(source["sha256"], "pending")
    if _head_has(converged_rel, env):
        print("bake retry converged on refreshed origin", flush=True)
        refresh_projection_status(env)
        return "pushed" if recorded == "pushed" else "unchanged"
    if _head_has(pending_rel, env):
        print("bake retry deferred after one bounded attempt; projection pending", flush=True)
        refresh_projection_status(env)
        return "pushed" if recorded == "pushed" else "unchanged"
    print(
        "bake retry failed after one bounded attempt; no matching projection receipt",
        flush=True,
    )
    refresh_projection_status(env)
    return "push-fail"


'''
text = text.replace(marker, "\n" + helper + "def _record_paths(env):\n", 1)

old = '''            if retry == "pushed":
                print("bake retry pushed from refreshed origin", flush=True)
                refresh_projection_status(env)
                return "pushed"
            if recorded == "pushed":
                print("bake retry deferred after one bounded attempt; record is durable", flush=True)
                refresh_projection_status(env)
                return "pushed"
            print("bake retry failed after one bounded attempt", flush=True)
            refresh_projection_status(env)
            return "push-fail"
'''
new = '''            if retry == "pushed":
                print("bake retry pushed from refreshed origin", flush=True)
                refresh_projection_status(env)
                return "pushed"
            if retry == "bake-reset":
                return _classify_bounded_bake_reset(env, recorded)
            if recorded == "pushed":
                print("bake retry deferred after one bounded attempt; record is durable", flush=True)
                refresh_projection_status(env)
                return "pushed"
            print("bake retry failed after one bounded attempt", flush=True)
            refresh_projection_status(env)
            return "push-fail"
'''
if text.count(old) != 1:
    raise SystemExit(f"unexpected retry block count: {text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
