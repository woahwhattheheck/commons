class ValidationError(ValueError):
    pass

def require_text(value, label):
    if not isinstance(value, str) or not value or len(value) > 512:
        raise ValidationError(label + " must be bounded text")
    return value

def require_rows(rows, key_fields, compare_fields):
    if not isinstance(rows, list) or len(rows) > 5000:
        raise ValidationError("rows must be a bounded list")
    required = set(key_fields) | set(compare_fields)
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != required:
            raise ValidationError("row fields do not match policy")
        key = tuple(row[field] for field in key_fields)
        if key in seen:
            raise ValidationError("duplicate row key")
        seen.add(key)
    return rows
