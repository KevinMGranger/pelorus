"""
Unified configuration management and parameter logging.

Configuration management needs to be consistent, and easy to get right.
Configuration should be logged in order to make debugging easier.
However, it must be hard to accidentally log sensitive information (API credentials, etc.).

This module handles the above goals by using `dataclasses`.

# A Simple Example

```python
@dataclass
class MyConfiguration:
    username: str = "GVR"
    password: str
    namespaces: list[str]
```

Calling `load(MyConfiguration)` will perform the following:

1. Look for the environment variable `USERNAME`.
2. Look for the environment variable `PASSWORD`.
3. Look for the environment variable `NAMESPACES` and split at each comma, stripping all whitespace.
3. Call `MyConfiguration(...)` with those values.
  If `USERNAME` is missing, it will default to `GVR`.
  If `PASSWORD` is missing, a TypeError will be thrown.
  If `NAMESPACES` is present but empty, an empty list will be given.

With that instance, calling `format(instance)` will yield an iterable.
The first element is the class's name (MyConfiguration),
and the following elements represent each field:

2. `username=GVR`
3. `password=REDACTED`.
  Any field name that contains any word in `REDACT_WORDS` will not be printed by default.

# Supported Variable Types

| type      | transformation from str                                 |
|-----------|---------------------------------------------------------|
| str       | set as-is                                               |
| bool      | distutils.util.strtobool                                |
| list[str] | split on `,` with whitespace stripped from each element |
| set[str]  | same as above                                           |

# Customization

You may need to deviate from the default behavior, or pass an argument that won't come from the environment.
You can customize each field with `var`:

@dataclass
class AdvancedConfiguration:
    anonymous_user: str = var(log=False)
    should_pass_tests: bool = var(log=True)
    whoami: str = var(env_lookups=["API_USER", "USER"])
    optional_name: str = var(default="someone")
    optional_list: list[str] = var(factory=list)
    api_client: Client = var(env_lookups=None)

Notable differences:
- anonymous_user will not be logged, when it otherwise would be.
- should_pass_tests _will_ be logged.
  We'd assume it's sensitive because it has "pass" in it, so we override that behavior.
- whoami is set to the first value found of either `API_USER` or `USER`, instead of looking at `WHOAMI`.
- optional_name and optional_list are optional.

api_client is not looked for at all. You will need to pass it when using `load`:
`load(AdvancedConfiguration, other=dict(api_client=client_instance))`

# Details

See each individual function for details.
"""

# TODO: this entire module would be cleaner if we had 3.10's `match`.


# TODO: we should consider making this one decorator.
# This could change the class's __str__ for you, making sure
# credentials aren't accidentally printed anywhere.
# Making this work with typing is really, really hard though.
# Using a parent class mix-in _could_ work,
# but we'd need to check that the child class used the dataclass decorator.
# Is that even possible? If it is, is it worth the complexity?


# @dataclass
# class CommittimeExporterConfig:
#     test: str
# user: str = field(default=2)
# user: str = var(default=2)
# user: str = field(metadata=config(env_lookups=["GIT_USER", "GITHUB_USER", "USER"]))
# token: str  # will not be logged
# sensitive_argument: str = field(metadata=config(log=True))  # will not be logged
# major_key: str = field(metadata=config(log=False))  # will be logged
# namespaces: list[str] = field(factory=list)


from typing import Any, Callable, Literal, Optional, Sequence, TypeVar, Union, overload

import attrs

from pelorus.config._class_setup import config
from pelorus.config.common import NothingDict
from pelorus.config.loading import _ENV_LOOKUPS, load_from_env
from pelorus.config.logging import _SHOULD_LOG, values

from ._attrs_compat import NOTHING


def _maybe_set(dict_: dict[str, Any], key: str, value: Union[Any, Literal[NOTHING]]):
    if value is not NOTHING:
        dict_[key] = value


FieldType = TypeVar("FieldType")


@overload
def var(
    *,
    default: FieldType,
    log: Optional[bool] = None,
    env_lookups: Union[Sequence[str], None, Literal[NOTHING]] = NOTHING,
    other_field_args: dict[str, Any] = {},
) -> FieldType:
    ...


@overload
def var(
    *,
    factory: Callable[[], FieldType],
    log: Optional[bool] = None,
    env_lookups: Union[Sequence[str], None, Literal[NOTHING]] = NOTHING,
    other_field_args: dict[str, Any] = {},
) -> FieldType:
    ...


@overload
def var(
    *,
    log: Optional[bool] = None,
    env_lookups: Union[Sequence[str], None, Literal[NOTHING]] = NOTHING,
    other_field_args: dict[str, Any] = {},
) -> Any:
    ...


def var(
    *,
    default: Any = NOTHING,
    factory: Any = NOTHING,
    log: Optional[bool] = None,
    env_lookups: Union[Sequence[str], None, Literal[NOTHING]] = NOTHING,
    other_field_args: dict[str, Any] = {},
):
    """
    Customize a variable in a config class.
    See `load`'s documentation for the default behavior.

    This is a convenience wrapper over `dataclasses.field`.

    `default` will be used if the variable is not found in the environment.
    Use `factory` if the default is mutable (e.g. a list).

    `log` manually controls if the field is logged, disregarding the automatic "redact" check.

    `env_lookups` list the names to check in the environment for the variable's value, in order.
    If an empty list or None, the environment will not be checked, and the argument should be given
    in `load`'s `other` dict.

    `other_field_args` are passed to `dataclasses.field`.


    See also: `dataclasses.field`.
    """
    metadata = NothingDict({_SHOULD_LOG: log, _ENV_LOOKUPS: env_lookups})

    args = NothingDict(
        **other_field_args, metadata=metadata, default=default, factory=factory
    )

    return attrs.field(**args)


__all__ = ["load_from_env", "values", "var", "config"]
