import os
from typing import Any, Mapping, Type, TypeVar

from attrs import fields

from pelorus.config._attrs_compat import NOTHING
from pelorus.config.loading.env import _ENV_LOOKUPS, ValueFinder
from pelorus.config.loading.errors import MissingConfigDataError, MissingDataError

ConfigClass = TypeVar("ConfigClass")


def load_from_env(
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
    kwargs = dict(other)

    missing: list[MissingDataError] = []

    for f in fields(cls):
        try:
            value = ValueFinder(f, env).find(other)
            if value is not NOTHING:
                kwargs[f.name] = value
        except MissingDataError as e:
            missing.append(e)

    if missing:
        raise MissingConfigDataError(cls.__name__, missing)

    return cls(**kwargs)


__all__ = ["load_from_env", "MissingConfigDataError", "_ENV_LOOKUPS"]
