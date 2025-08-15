"""
High-level sanitizer for pytr payloads using DataSON redaction.
"""
from typing import Any, List, Optional, Pattern

from datason.redaction import RedactionEngine, RedactionSummary, RedactionAuditEntry

# Default fields and regex patterns to redact
DEFAULT_FIELDS: List[str] = [
    "phone", "pin", "*.iban", "*.isin", "*.currency", "*.amount"
]
# Common regex patterns for sensitive formats
DEFAULT_PATTERNS: List[str] = [
    r"\b[A-Z]{2}\d{2}[A-Z0-9]{1,30}\b",  # IBAN
    r"\b[A-Z]{2}[A-Z0-9]{9,17}\b",       # ISIN
    r"\b\d+[.,]?\d*\s?[A-Z]{3}\b",    # Currency amounts like '100.00 USD'
]


def sanitize(
    data: Any,
    redact_fields: Optional[List[str]] = None,
    redact_patterns: Optional[List[str]] = None,
    audit: bool = False,
) -> Any:
    """
    Sanitize an arbitrary payload by redacting sensitive fields and patterns.

    :param data: Incoming payload (dict, list, etc.)
    :param redact_fields: Optional field-glob patterns to redact (overrides defaults)
    :param redact_patterns: Optional regex patterns to redact (overrides defaults)
    :param audit: If True, include audit trail entries and summary in output
    :returns: Redacted payload; if audit=True, returns dict with keys:
        {'data': redacted_data, 'audit': [RedactionAuditEntry], 'summary': RedactionSummary}
    """
    engine = RedactionEngine(
        redact_fields=redact_fields or DEFAULT_FIELDS,
        redact_patterns=redact_patterns or DEFAULT_PATTERNS,
        audit_trail=audit,
        include_redaction_summary=audit,
    )
    redacted = engine.process_object(data)
    if audit:
        return {
            "data": redacted,
            "audit": engine._audit_entries,
            "summary": engine._summary,
        }
    return redacted
