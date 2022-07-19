from typing import Mapping, Optional

import attrs
from attr import NOTHING
from attrs import Attribute

from pelorus.config._common import _PELORUS_CONFIG_VALUE_SOURCES

REDACT_WORDS = {"pass", "token", "key", "cred", "secret"}
"""
Variables containing these words are not logged by default, nor are attributes starting with an underscore.
"""

_SHOULD_LOG = "__pelorus_config_log"


def _should_be_logged(f: Attribute) -> Optional[bool]:
    """
    A field should NOT be logged if it explicitly marked as such,
    or contains a word that implies it is sensitive (members of REDACT_WORDS).

    If `None` is returned, then the key should not even be listed (an internal/private value).
    """
    log = f.metadata.get(_SHOULD_LOG, NOTHING)

    if log is NOTHING:
        is_private = f.name.startswith("_")
        should_be_redacted = any(word in f.name.lower() for word in REDACT_WORDS)
        if is_private:
            return None
        elif should_be_redacted:
            return False
        else:
            return True
    elif log is None:
        return None
    else:
        return bool(log)


def format_values(obj: object):
    """
    Yields each field formatted as name=value,
    redacting the value for sensitive fields.
    """
    value_sources: Mapping[str, str] = getattr(
        obj, _PELORUS_CONFIG_VALUE_SOURCES, dict()
    )

    for f in attrs.fields(type(obj)):
        should_be_logged = _should_be_logged(f)
        if should_be_logged is None:
            continue
        elif should_be_logged:
            value = getattr(obj, f.name)
        else:
            value = "REDACTED"

        if f.name in value_sources:
            source = f"({value_sources[f.name]})"
        else:
            source = ""
        yield f"{f.name}={value}{source}"
