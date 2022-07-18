"""
Unified configuration management and parameter logging.

Configuration management needs to be consistent, and easy to get right.
Configuration should be logged in order to make debugging easier.
However, it must be hard to accidentally log sensitive information (API credentials, etc.).

This module handles the above goals by using `attrs`.

# A Simple Example

```python
from pelorus.config import config, load_from_env, var

@config
class MyConfiguration:
    username: str = "GVR"
    password: str
    namespaces: list[str]
```

Calling `load_from_env(MyConfiguration)` will perform the following:

1. Look for the environment variable `USERNAME`.
2. Look for the environment variable `PASSWORD`.
3. Look for the environment variable `NAMESPACES` and split at each comma, stripping all whitespace.
3. Call `MyConfiguration(...)` with those values.
  If `USERNAME` is missing, it will default to `GVR`.
  If `PASSWORD` is missing, a TypeError will be thrown.
  If `NAMESPACES` is present but empty, an empty list will be given.

With that instance, calling `format_values(instance)` will yield an iterable,
one element per field:

2. `username=GVR`
3. `password=REDACTED`.
  Any field name that contains any word in `REDACT_WORDS` will not be printed by default.

# Supported Variable Types

| type      | transformation from str                                 |
|-----------|---------------------------------------------------------|
| str       | set as-is                                               |
| list[str] | split on `,` with whitespace stripped from each element |
| set[str]  | same as above                                           |

Other types may be supported with customization and converters:

# Customization

You may need to deviate from the default behavior, or pass an argument that won't come from the environment.
You can customize each field with `var`:

@config
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
`load_from_env(AdvancedConfiguration, other=dict(api_client=client_instance))`

## Converters

`var` wraps `attrs.field`. You can support fancier type transformations using converters.
Attrs even allows them to be composed.

You should consider supporting passing in an object of the target type,
having each converter skip it if it's already correct.

```python
from typing import Optional
from pelorus.config import vars, config
from pelorus.config.converters import comma_separated
from attrs.converters import default_if_none

def treat_empty_str_as_none(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    else:
        return value


@config
class FancyConfig:
    not_quite_a_list: SomeCollection[str] = var(field_args=dict(
            converters=comma_separated(SomeCollection)
            ))

    required_int_with_empty_as_zero: int = var(field_args=dict(
            converters=[treat_empty_str_as_none, default_if_none(default=0), int]
    ))
```

The env vars:
NOT_QUITE_A_LIST="foo,bar"
REQUIRED_INT_WITH_EMPTY_AS_ZERO="3"

Will result in the equivalent of:
```python
FancyConfig(
    not_quite_a_list=SomeCollection("foo", "bar"),
    required_int_with_empty_as_zero=4
    )
```

While the env vars:
NOT_QUITE_A_LIST=""
REQUIRED_INT_WITH_EMPTY_AS_ZERO=""

Will result in the equivalent of:
```python
FancyConfig(
    not_quite_a_list=SomeCollection(),
    required_int_with_empty_as_zero=0
    )
```

# Details

See each individual function for details.

# Development

See [DEVELOPING.md](./DEVELOPING.md) for details.
"""

# TODO: this entire module would be cleaner if we had 3.10's `match`.

from typing import Any, Callable, Literal, Optional, Sequence, TypeVar, Union, overload

import attrs

from pelorus.config._class_setup import config
from pelorus.config._common import NothingDict
from pelorus.config.loading import _ENV_LOOKUPS, load_from_env
from pelorus.config.logging import _SHOULD_LOG, format_values

from ._attrs_compat import NOTHING

FieldType = TypeVar("FieldType")

# TODO: make converters first-class if we can?
# That might really mess with the typing, which I don't want to do.
# Is this something that 3.10 could do with typing.ParamSpec and typing.Concat ?


@overload
def var(
    *,
    default: FieldType,
    log: Optional[bool] = None,
    env_lookups: Union[Sequence[str], None, Literal[NOTHING]] = NOTHING,
    field_args: dict[str, Any] = {},
) -> FieldType:
    ...


@overload
def var(
    *,
    factory: Callable[[], FieldType],
    log: Optional[bool] = None,
    env_lookups: Union[Sequence[str], None, Literal[NOTHING]] = NOTHING,
    field_args: dict[str, Any] = {},
) -> FieldType:
    ...


@overload
def var(
    *,
    log: Optional[bool] = None,
    env_lookups: Union[Sequence[str], None, Literal[NOTHING]] = NOTHING,
    field_args: dict[str, Any] = {},
) -> Any:
    ...


def var(
    *,
    default: Any = NOTHING,
    factory: Any = NOTHING,
    log: Optional[bool] = None,
    env_lookups: Union[Sequence[str], None, Literal[NOTHING]] = NOTHING,
    field_args: dict[str, Any] = {},
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
        **field_args, metadata=metadata, default=default, factory=factory
    )

    return attrs.field(**args)


__all__ = ["load_from_env", "format_values", "var", "config"]
