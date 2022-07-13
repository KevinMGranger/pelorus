from dataclasses import MISSING, Field, fields, is_dataclass
from typing import Any, Literal, Union, cast

REDACT_WORDS = {"pass", "token", "key", "cred", "secret"}
"""
Variables containing these words are not logged by default.
"""

_LOG_METADATA_KEY = "__pelorus_config_log"


def _should_be_logged(f: Field) -> bool:
    """
    A field should NOT be logged if it explicitly marked as such,
    or contains a word that implies it is sensitive (members of REDACT_WORDS).
    """
    log: Union[bool, None, Literal[MISSING]] = f.metadata.get(_LOG_METADATA_KEY)
    if log is MISSING:
        name_is_redactable = any(word in f.name.lower() for word in REDACT_WORDS)
        return not name_is_redactable
    else:
        return bool(log)


def format(obj: Any):
    """
    Yields the name of the class followed by its members,
    redacting any fields that should not be logged.
    """
    if not is_dataclass(obj):
        raise TypeError("format must be passed a dataclass")

    yield cast(str, obj.__name__)

    for f in fields(obj):
        if not _should_be_logged(f):
            value = "REDACTED"
        else:
            value = getattr(obj, f.name)

        yield f"{f.name}={value}"
