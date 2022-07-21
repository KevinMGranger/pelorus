from typing import Mapping, Optional

import attrs
from attr import NOTHING
from attrs import Attribute

from pelorus.config._common import _PELORUS_CONFIG_VALUE_SOURCES




def _should_be_logged(f: Attribute) -> Optional[bool]:
    log = f.metadata.get(_SHOULD_LOG, NOTHING)

    if log is NOTHING:
        is_private = f.name.startswith("_")
        if is_private:
            return None

        should_be_redacted = any(word in f.name.lower() for word in REDACT_WORDS)
        if should_be_redacted:
            return False

        return True
    elif log is None:
        return None
    else:
        return bool(log)


def format_values(obj: object):
    """
    Yields each field formatted as name=value, redacting the value for sensitive fields.
    Will skip fields that are private.
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
            if isinstance(value, str):
                value = repr(value)
        else:
            value = "REDACTED"

        if f.name in value_sources:
            source = f"\t({value_sources[f.name]})"
        else:
            source = ""
        yield f"{f.name}={value}{source}"
