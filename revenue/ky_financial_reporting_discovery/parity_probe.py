from .probe import exact_equal, row_key

def compare_rows(legacy_rows, target_rows, key_fields, compare_fields):
    legacy = {row_key(row, key_fields): row for row in legacy_rows}
    target = {row_key(row, key_fields): row for row in target_rows}
    findings = []
    for key in sorted(set(legacy) | set(target), key=repr):
        left = legacy.get(key)
        right = target.get(key)
        if left is None:
            findings.append(("EXTRA_TARGET_ROW", key, None))
            continue
        if right is None:
            findings.append(("MISSING_TARGET_ROW", key, None))
            continue
        for field in compare_fields:
            if not exact_equal(left[field], right[field]):
                findings.append(("VALUE_DRIFT", key, field))
    return findings
