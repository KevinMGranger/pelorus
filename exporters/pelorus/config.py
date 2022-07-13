"""
Unified configuration management and parameter logging.
"""

# TODO: transformation for lists

from dataclasses import Field, dataclass, field, fields, is_dataclass
from typing import Any, Optional, Type, TypeVar

import pelorus.utils

__REDACT_KEY = "__pelorus_config_redact"
__ENV_LOOKUPS_KEY = "__pelorus_config_env_lookups"

REDACT_WORDS = {"pass", "token", "key", "cred"}


def config(
    *, redact: Optional[bool] = None, env_lookups: Optional[list[str]] = None
) -> dict[str, Any]:
    return {__REDACT_KEY: redact, __ENV_LOOKUPS_KEY: env_lookups}


def should_be_logged(f: Field) -> bool:
    """
    A field should NOT be logged if it explicitly marked as redacted,
    or contains a word that implies it is sensitive (members of REDACT_WORDS).
    """
    redact = f.metadata.get(__REDACT_KEY)
    if redact is None and any(word in f.name.lower() for word in REDACT_WORDS):
        redact = True

    return bool(redact)


def log(obj: Any):
    """
    Logs each member of the dataclass,
    unless it is a sensitive value.
    """
    if not is_dataclass(obj):
        # TODO
        return

    # TODO: real logging
    print(obj.__name__)

    for f in fields(obj):
        if not should_be_logged(f):
            value = "REDACTED"
        else:
            value = getattr(obj, f.name)

        # TODO: indentation, perhaps?
        print(f"{f.name}={value}")


T = TypeVar("T")


def load(cls: Type[T], other: dict[str, Any] = {}) -> T:
    """
    Loads the dataclass from env vars,
    overriding values with anything given in `other`.
    """
    if not is_dataclass(cls):
        # TODO
        raise TypeError

    field_args = {}

    for f in fields(cls):
        env_lookups = f.metadata.get(__ENV_LOOKUPS_KEY)

        if env_lookups is None:
            env_lookups = [f.name.upper()]
        elif not env_lookups:
            # deliberately given an empty list,
            # meaning this should only be provided through `other`.
            continue
        # else env_lookups is a list with at least 1 member.

        value = None
        for name in env_lookups:
            value = pelorus.utils.get_env_var(name)
            if value is not None:
                break
        else:
            # not found in env: will either come from `other`,
            # the default will come from `cls`,
            # or `cls` will throw an error.
            continue

        if f.type in (list, set):
            value = f.type(part.strip() for part in value.split(","))

        field_args[f.name] = value

    return cls(**field_args, **other)


@dataclass
class CommittimeExporterConfig:
    user: str = field(metadata=config(env_lookups=["GIT_USER", "GITHUB_USER", "USER"]))
    token: str  # will not be logged
    sensitive_argument: str = field(metadata=config(redact=True))  # will not be logged
    major_key: str = field(metadata=config(redact=False))  # will be logged
    namespaces: list[str] = field(default_factory=list)
