import os
from typing import Any, Mapping, Type, TypeVar

from pelorus.config.loading._errors import MissingConfigDataError
from pelorus.config.loading.env import _ENV_LOOKUPS_KEY, EnvironmentConfigLoader

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
    """
    return EnvironmentConfigLoader(cls, other, env).construct()


__all__ = ["load_from_env", "MissingConfigDataError", "_ENV_LOOKUPS_KEY"]
