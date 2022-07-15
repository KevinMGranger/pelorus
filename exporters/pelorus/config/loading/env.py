import typing
from dataclasses import MISSING, Field, dataclass
from distutils.util import strtobool
from functools import cached_property
from typing import (
    Any,
    Callable,
    Collection,
    Generic,
    Mapping,
    Optional,
    Sequence,
    TypeVar,
    Union,
)

from pelorus.config.loading.common import _DEFAULT_KEYWORD
from pelorus.config.loading.errors import MissingDefault, MissingOther, MissingVariable

_ENV_LOOKUPS = "__pelorus_config_env_lookups"

# TODO: the way we're doing it, "unset" and "DEFAULT" are treated the same if a default is set.
# That's the way get_env_vars currently does it.
# But are we taking away the option to have `Optional[str]`?
# We don't support that right now anyway, but is there a use case for that?
# I'll argue no, since it's impossible to unset a var already set in openshift.
# TODO: now, counting an empty as unset: yes. that's worth doing Optional for.
# We need to discuss that though, since that's not how `get_env_vars` works.

ValueType = TypeVar("ValueType")


@dataclass
class ValueFinder(Generic[ValueType]):
    """
    A ValueFinder looks for the value described by `field` in the environment `env`.
    """

    field: Field[ValueType]
    env: Mapping[str, str]

    @cached_property
    def env_lookups(self) -> Sequence[str]:
        """
        Gets the list of environment variable names to look up for this field.
        Will default to the field name in uppercase.  If disabled, will return an empty sequence.
        """
        field_name = self.field.name

        if _ENV_LOOKUPS not in self.field.metadata:
            # default to the variable's name in uppercase.
            return [field_name.upper()]

        env_lookups: Optional[Sequence[str]] = self.field.metadata[_ENV_LOOKUPS]

        return env_lookups if env_lookups is not None else tuple()

    def all_matches(self):
        """
        Yield all name-value pairs that were present in the mapping.
        """
        for name in self.env_lookups:
            value = self.env.get(name)
            if value is not None:
                yield (name, value)

    def _get_default(self, env_name: Optional[str]) -> ValueType:
        """
        Get the default value for this field.
        `env_name` is used for error reporting if the default is not present.
        """
        if self.field.default is not MISSING:
            return self.field.default
        elif self.field.default_factory is not MISSING:
            return self.field.default_factory()
        else:
            if env_name is not None:
                raise MissingDefault(self.field.name, env_name)
            else:
                raise MissingVariable(self.field.name, self.env_lookups)

    def transform_value(self, value: str) -> ValueType:
        """
        Transforms a given value based on the type argument:

        If a boolean, use strtobool.
        If a collections.abc.Collection (that is also callable), split on ',', strip whitespace.
        If an Optional, ignore, since we already have a value.

        TODO: arbitrarily nested data types probably aren't necessary, but would be easily done here.
        """

        type_ = self.field.type

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

    def find(self, other: dict[str, Any]):
        """
        Find (and convert) the value for this field,
        using `other` if it should override or be preferred.
        """
        env_lookups = self.env_lookups
        if not env_lookups:
            # deliberately given an empty list or None,
            # meaning this should be provided through `other`.
            if self.field.name in other:
                return other[self.field.name]
            else:
                raise MissingOther(self.field.name)

        for env_name, env_value in self.all_matches():
            if env_value == _DEFAULT_KEYWORD:
                return self._get_default(env_name)
            return self.transform_value(env_value)

        return self._get_default(None)
