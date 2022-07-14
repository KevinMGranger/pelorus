import os
from dataclasses import fields, is_dataclass
from typing import Any, Mapping, Type, TypeVar

from pelorus.config.loading.env import ValueFinder
from pelorus.config.loading.errors import MissingConfigDataError, MissingDataError

ConfigClass = TypeVar("ConfigClass")


def load(
    cls: Type[ConfigClass],
    other: dict[str, Any] = {},
    *,
    env: Mapping[str, str] = os.environ,
) -> ConfigClass:
    """
    Construct the `cls`, looking up variables in `env` (the OS's environment by default),
    overriding them with the contents of `other`.

    See this module's documentation for details.
    """
    if not is_dataclass(cls):
        raise TypeError("load must be passed a dataclass")

    field_args = dict(other)

    missing: list[MissingDataError] = []

    for f in fields(cls):
        try:
            field_args[f.name] = ValueFinder(f, env).find(other)
        except MissingDataError as e:
            missing.append(e)

    if missing:
        raise MissingConfigDataError(cls.__name__, missing)

    return cls(**field_args)
