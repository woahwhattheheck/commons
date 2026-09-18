class ValidationError(ValueError):
    pass

def require_rows(rows):
    if not isinstance(rows, list):
        raise ValidationError("rows must be a list")
    if len(rows) > 5000:
        raise ValidationError("too many rows")
    for row in rows:
        if not isinstance(row, dict):
            raise ValidationError("each row must be an object")
    return rows
