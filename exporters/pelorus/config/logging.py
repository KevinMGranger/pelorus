import attrs
from attrs import Attribute

REDACT_WORDS = {"pass", "token", "key", "cred", "secret"}
"""
Variables containing these words are not logged by default.
"""

_SHOULD_LOG = "__pelorus_config_log"


def _should_be_logged(f: Attribute) -> bool:
    """
    A field should NOT be logged if it explicitly marked as such,
    or contains a word that implies it is sensitive (members of REDACT_WORDS).
    """
    log = f.metadata.get(_SHOULD_LOG)
    if log is None:
        appears_safe_to_log = all(word not in f.name.lower() for word in REDACT_WORDS)
        return appears_safe_to_log
    else:
        return bool(log)


def values(obj: object):
    """
    Yields each field formatted as name=value,
    redacting the value for sensitive fields.
    """

    for f in attrs.fields(type(obj)):
        if _should_be_logged(f):
            value = getattr(obj, f.name)
        else:
            value = "REDACTED"

        yield f"{f.name}={value}"
