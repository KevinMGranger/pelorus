"""
Unified configuration management and parameter logging.
"""

# TODO: transformation for lists

from dataclasses import fields, is_dataclass
from typing import Any, Optional

__REDACT_KEY = "__pelorus_config_redact"
__FROM_ENV_KEY = "__pelorus_config_from_env"

REDACT_WORDS = ("pass", "token", "key", "cred")


def config(*, redact: Optional[bool] = None, from_env: bool = True) -> dict[str, Any]:
    return {__REDACT_KEY: redact, __FROM_ENV_KEY: from_env}


def log(obj: Any):
    if not is_dataclass(obj):
        # TODO
        return

    # TODO: real logging
    print(obj.__name__)

    for field in fields(obj):
        redact = field.metadata.get(__REDACT_KEY)
        if redact is None and any(word in field.name.lower() for word in REDACT_WORDS):
            redact = True

        if redact:
            continue

        # TODO: indentation, perhaps?
        print(f"{field.name}={getattr(obj, field.name)}")


# TODO: load from env vars.
# TODO: make typing correct.
def load(cls: type) -> type:
    ...
