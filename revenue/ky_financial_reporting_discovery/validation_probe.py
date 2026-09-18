class ValidationError(ValueError):
    pass

def require_text(value):
    if not isinstance(value, str):
        raise ValidationError("value must be text")
    return value
