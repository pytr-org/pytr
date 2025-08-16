# pytr/errors.py

class ApiShapeError(Exception):
    """Raised when API response shape is unexpected."""
    def __init__(self, message, *, data=None):
        super().__init__(message)
        self.data = data

def redact_sensitive_data(data):
    """Redacts sensitive data from a dictionary."""
    if not isinstance(data, dict):
        return data
    redacted = data.copy()
    for key in redacted.keys():
        if "token" in key.lower() or "pin" in key.lower():
            redacted[key] = "<redacted>"
    return redacted
