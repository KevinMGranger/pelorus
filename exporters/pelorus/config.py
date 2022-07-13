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
    optional_list: list[str] = var(default_factory=list)
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

import os
import typing
from dataclasses import MISSING, Field, field, fields, is_dataclass
from distutils.util import strtobool
from typing import (
    Any,
    Callable,
    Collection,
    Literal,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    cast,
)

import pelorus.utils

_DEFAULT_KEYWORD = (
    os.getenv("PELORUS_DEFAULT_KEYWORD") or pelorus.utils.DEFAULT_VAR_KEYWORD
)

__LOG_METADATA_KEY = "__pelorus_config_log"
__ENV_LOOKUPS_METADATA_KEY = "__pelorus_config_env_lookups"

REDACT_WORDS = {"pass", "token", "key", "cred", "secret"}
"""
Variables containing these words are not logged by default.
"""


NoEnv = tuple()
"""
The config variable should not be looked up in the environment.
It will be passed manually to `load`'s `other` dict.

You can also pass `None`.
"""

FieldType = TypeVar("FieldType")


def var(
    *,
    default: Union[FieldType, Literal[MISSING]] = MISSING,
    default_factory: Union[Callable[[], FieldType], Literal[MISSING]] = MISSING,
    log: Union[bool, None, Literal[MISSING]] = None,
    env_lookups: Union[Sequence[str], None, Literal[MISSING]] = MISSING,
    other_field_args: dict[str, Any] = {},
) -> Field[FieldType]:
    """
    Customize a variable in a config class.
    See `load`'s documentation for the default behavior.

    This is a convenience wrapper over `dataclasses.field`.

    `default` will be used if the variable is not found in the environment.
    Use `default_factory` if the default is mutable (e.g. a list).

    `log` manually controls if the field is logged, disregarding the automatic "redact" check.

    `env_lookups` list the names to check in the environment for the variable's value, in order.
    If an empty list or None, the environment will not be checked, and the argument should be given
    in `load`'s `other` dict.

    `other_field_args` are passed to `dataclasses.field`.


    See also: `dataclasses.field`.
    """
    args = other_field_args | dict(
        metadata={__LOG_METADATA_KEY: log, __ENV_LOOKUPS_METADATA_KEY: env_lookups}
    )

    return field(**args)


def _should_be_logged(f: Field) -> bool:
    """
    A field should NOT be logged if it explicitly marked as such,
    or contains a word that implies it is sensitive (members of REDACT_WORDS).
    """
    log: Union[bool, None, Literal[MISSING]] = f.metadata.get(__LOG_METADATA_KEY)
    if log is MISSING:
        name_is_redactable = any(word in f.name.lower() for word in REDACT_WORDS)
        return not name_is_redactable
    else:
        return bool(log)


def format(obj: Any):
    """
    Yields the name of the class followed by its members,
    redacting any fields that should not be logged.
    """
    if not is_dataclass(obj):
        raise TypeError("format must be passed a dataclass")

    yield cast(str, obj.__name__)

    for f in fields(obj):
        if not _should_be_logged(f):
            value = "REDACTED"
        else:
            value = getattr(obj, f.name)

        yield f"{f.name}={value}"


MetadataType = TypeVar("MetadataType")


def _get_metadata_value(
    metadata: Mapping[str, Any],
    key: str,
    type_: Type[MetadataType],
) -> Union[MetadataType, Literal[MISSING]]:
    """
    Get the metadata with the given key.
    A missing value will always return `MISSING`, and the type will be cast.

    Without this, `key in metadata` will be true even if it falls back to the
    sentinel value of `MISSING`.
    """
    value = metadata.get(key, MISSING)
    if value is not MISSING:
        return cast(type_, value)
    else:
        return value


class DefaultValue:
    """
    The env var was set to the configured "default" keyword.
    """

    def __bool__(self):
        return False


def _get_env_var(
    var_name: str, *, env: Mapping[str, str]
) -> Union[str, None, DefaultValue]:
    """
    See pelorus.utils.get_env_var.  Similar, but makes fewer choices for you.

    Returns the str if it is set, None if unset,
    or DefaultValue() if set to the configured "default" keyword.
    """
    default_keyword = ()

    env_var = os.getenv(var_name)
    if env_var == default_keyword:
        return DefaultValue()
    else:
        return env_var


class MissingVariable(NamedTuple):
    """
    A required variable was missing.
    """

    name: str
    env_lookups: Sequence[str]

    def __str__(self):
        if len(self.env_lookups) == 1:
            env_lookup_str = f"env var {self.env_lookups[0]}"
        else:
            env_lookup_str = "any of " + ",".join(self.env_lookups)

        return f"{self.name} was not found in {env_lookup_str}"


class MissingDefault(NamedTuple):
    """
    A variable was set to "default" but there was no default set.
    """

    name: str
    var_containing_default: str

    def __str__(self):
        return f"{self.name} was set to {_DEFAULT_KEYWORD} in env var {self.var_containing_default} but there was no default set"


class MissingOther(NamedTuple):
    """
    A variable had environment lookups disabled, but was not passed in `other`.
    """

    name: str

    def __str__(self):
        return f"{self.name} had environment lookups disabled, but was not passed in to `load`'s `other` dict."


MissingErrorType = Union[MissingVariable, MissingDefault, MissingOther]


class MissingConfigDataError(Exception):
    """
    Collects all missing env var issues into one error.
    """

    def __init__(self, config_class: str, missing: Collection[MissingErrorType]):
        super().__init__()
        self.config_class = config_class
        self.missing = missing

    def __str__(self):
        return f"Config for {self.config_class} is missing data: " + "\n".join(
            str(x) for x in self.missing
        )


ConfigValueType = TypeVar("ConfigValueType")


def transform_value(value: str, type_: Type[ConfigValueType]) -> ConfigValueType:
    """
    Transforms a given value based on the type argument:

    If a boolean, use strtobool.
    If a collections.abc.Collection (that is also callable), split on ',', strip whitespace.
    If an Optional, ignore, since we already have a value.

    TODO: maybe the rest should be abstracted too.

    TODO: arbitrarily nested data types probably aren't necessary, but would be easily done here.
    """

    # plain 'ol types first
    if type_ is str:
        return value  # type: ignore
    elif type_ is bool:
        return strtobool(value)  # type: ignore

    # generic types next.
    # for fancy typing like `list[str]` or `Optional[str]`, we look at the "origin" and "args".
    # list[str]'s origin is `list`, and its args are `(str,)`.
    # Optional[str]'s origin is `typing.Union` and its args are `(str, type(None))`
    # (since Optional is just an alias for Union[None, OTHER_TYPE])

    generic_origin = typing.get_origin(type_)
    generic_args = typing.get_args(type_)

    if generic_origin is Union and set(generic_args) == {str, type(None)}:
        # optional str, just return value since we already have it.
        return value  # type: ignore
    elif (
        generic_origin is not None
        and issubclass(generic_origin, Collection)
        and issubclass(generic_origin, Callable)
        and generic_args == (str,)
    ):
        # TODO: pyright says generic_origin is Never. Either I have a logic bug or they do.
        return generic_origin(part.strip() for part in value.split(","))

    raise TypeError(f"Unsupported type for config object: {type_}")


ConfigClass = TypeVar("ConfigClass")

# TODO: can we get a nicer error message than the default TypeError would give us?
# ANSWER: yes.

# TODO: the way we're doing it, "unset" and "DEFAULT" are treated the same if a default is set.
# That's the way get_env_vars currently does it.
# But are we taking away the option to have `Optional[str]`?
# We don't support that right now anyway, but is there a use case for that?
# I'll argue no, since it's impossible to unset a var already set in openshift.
# TODO: now, counting an empty as unset: yes. that's worth doing Optional for.
# We need to discuss that though, since that's not how `get_env_vars` works.
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

    missing: list[MissingErrorType] = []

    for f in fields(cls):
        field_name = f.name
        if field_name in field_args:
            # overridden from `other`, don't bother looking
            continue

        env_lookups = _get_metadata_value(
            f.metadata, __ENV_LOOKUPS_METADATA_KEY, Optional[Sequence[str]]
        )

        if env_lookups is MISSING:
            # default to the variable's name in uppercase.
            env_lookups = [field_name.upper()]
        elif not env_lookups:
            # deliberately given an empty list or None,
            # meaning this should only be provided through `other`.
            # However, if we didn't skip earlier, it must not be in other!
            missing.append(MissingOther(field_name))
            continue
        # else env_lookups is a list with at least 1 member.

        # TODO: should this be its own function?
        first_match = next(
            (
                (env_var_name, value)
                for env_var_name in env_lookups
                if (value := _get_env_var(env_var_name, env=env)) is not None
            ),
            None,
        )

        env_var_name, value = (None, None) if first_match is None else first_match

        # happy path:
        if env_var_name and isinstance(value, str):
            field_args[field_name] = transform_value(value, f.type)
        # otherwise...
        elif f.default is not MISSING:
            field_args[field_name] = f.default
        elif f.default_factory is not MISSING:
            field_args[field_name] = f.default_factory()
        # if we're here, it's an error. We just need to figure out which type.
        else:
            if env_var_name is not None and isinstance(value, DefaultValue):
                err = MissingDefault(field_name, env_var_name)
            else:
                err = MissingVariable(field_name, env_lookups)
            missing.append(err)

    if missing:
        raise MissingConfigDataError(cls.__name__, missing)

    return cls(**field_args)


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
# namespaces: list[str] = field(default_factory=list)
