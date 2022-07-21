"""
A declarative way to load configuration from environment variables, and log that configuration properly.

See the [README](./README.md) file for documentation.
See [DEVELOPING](./DEVELOPING.md) for implementation details / dev docs.
"""

import os
from typing import Any, Mapping, Type, TypeVar

import attrs

from pelorus.config.loading import (
    MissingConfigDataError,
    MissingDataError,
    ValueWithSource,
    _EnvFinder,
)
from pelorus.config.logging import REDACT, SKIP


def _prepare_kwargs(results: dict[str, Any]):
    """
    Handle the following cases:

    Attrs removes underscores from field names for the init param names,
    so we need to change the field names for the kwargs.

    We wrap values in classes describing where they came from, so we need to unpack those.
    """
    for k, v in results.items():
        if isinstance(v, ValueWithSource):
            value = v.value
        else:
            value = v

        yield k.lstrip("_"), value


ConfigClass = TypeVar("ConfigClass")

# TODO: init=False values should not be loaded


def load_and_log(
    cls: Type[ConfigClass],
    other: dict[str, Any] = {},
    *,
    env: Mapping[str, str] = os.environ,
    default_keyword: str = "default",
) -> ConfigClass:
    results: dict[str, Any] = dict()
    errors = []
    for field in attrs.fields(cls):
        if not field.init:
            # field does not get set during instance creation,
            # so don't load it.
            continue

        name = field.name

        value = _EnvFinder.get_value(field, env, other, default_keyword)

        if isinstance(value, MissingDataError):
            results[name] = value
            errors.append(value)
        else:
            results[name] = value

    if errors:
        print(
            f"While loading config {cls.__name__}, errors were encountered. All values:"
        )
    else:
        print(f"Loading {cls.__name__}, inputs below:")

    for field, value in results.items():
        if isinstance(value, ValueWithSource):
            if value.log is SKIP:
                continue

            source = value.source()

            if value.log is REDACT:
                value = "REDACTED"
            else:
                value = repr(value.value)

            print(f"{field}={value}", source)
        elif isinstance(value, MissingDataError):
            print(f"{field}=ERROR:", value)
        else:  # came from other, skip logging.
            pass

    if errors:
        raise MissingConfigDataError(cls.__name__, errors)

    kwargs = dict(_prepare_kwargs(results))

    return cls(**kwargs)
