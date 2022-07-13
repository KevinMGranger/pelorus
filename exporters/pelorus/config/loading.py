import os
import typing
from dataclasses import MISSING, fields, is_dataclass
from distutils.util import strtobool
from typing import (
    Any,
    Callable,
    Collection,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
)

import pelorus.utils
from pelorus.config.common import _get_metadata_value

_ENV_LOOKUPS_METADATA_KEY = "__pelorus_config_env_lookups"

_DEFAULT_KEYWORD = (
    os.getenv("PELORUS_DEFAULT_KEYWORD") or pelorus.utils.DEFAULT_VAR_KEYWORD
)


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
        return (
            f"{self.name} was set to {_DEFAULT_KEYWORD} "
            f"in env var {self.var_containing_default} but there was no default set"
        )


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
            f.metadata, _ENV_LOOKUPS_METADATA_KEY, Optional[Sequence[str]]
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
