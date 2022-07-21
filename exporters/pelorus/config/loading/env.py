from contextvars import ContextVar
import itertools
import os
from typing import (
    Any,
    Callable,
    Collection,
    Generic,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
)

import attrs
from attrs import Attribute, fields

from pelorus.config._attrs_compat import NOTHING, Factory
from pelorus.config._common import (
    _DEFAULT_KEYWORD,
    _PELORUS_CONFIG_VALUE_SOURCES,
    NothingDict,
)
from pelorus.config.loading._errors import (
    MissingConfigDataError,
    MissingDataError,
    MissingDefault,
    MissingOther,
    MissingVariable,
)
from yaml import load


config_env: ContextVar[Mapping[str, str]] = ContextVar("env", default=os.environ)
default_keyword: ContextVar[str] = ContextVar("default_keyword", default="default")


# TODO: generic?
class EnvVars(Factory):
    # not instantiated directly. Done via other functions.
    # This makes error handling / fallbacks so much easier.
    # this only needs logic to handle the case where lookups absolutely should happen!
    # and we can rely on it being configured, isntead of us doing it ourselves!

    name: str

    def __init__(
        self,
        env_vars: tuple[str],
        default: Union[Any, Literal[NOTHING], Factory],
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs, factory=self.load_from_env, takes_self=True)
        self.env_vars = env_vars
        self.default = default

    def _env_lookups_default_source(self) -> str:
        if len(self.env_vars) == 1:
            return f"default value; {self.env_vars[0]} was not set"
        else:
            return "default value; none of " + ", ".join(self.env_vars) + " were set"

    def _get_default(self) -> Union[Any, Literal[NOTHING]]:
        if self.default is NOTHING:
            return NOTHING

        if isinstance(self.default, Factory):
            if self.default.takes_self:
                return self.default.factory(loading_instance)  # type: ignore
            else:
                return self.default.factory()  # type: ignore
        else:
            return self.default

    def first_env_match(self) -> Optional[tuple[str, str]]:
        env = config_env.get()
        for name in self.env_vars:
            if name in env:
                return name, env[name]

        return None

    def _load(
        self,
    ) -> tuple[str, str]:
        if (result := self.first_env_match()) is None:
            if (value := self._get_default()) is NOTHING:
                raise MissingVariable(self.name, self.env_vars)

            return value, self._env_lookups_default_source()

        env_name, value = result

        if value == default_keyword.get():
            if (value := self._get_default()) is NOTHING:
                raise MissingDefault(self.name, env_name)

            return value, f"default value ({env_name} set to {value}"

        return value, f"from env var {env_name}"

    def load_from_env(self, loading_instance) -> str:
        value, source = self._load()
        getattr(loading_instance, )


# def env_vars(lookup: str, *lookups: str, default: Union[str, None, Literal[NOTHING]]):
#     all_lookups = tuple(lookup, *lookups)

#     def _lookup_from_env_vars(self):
#         env = _env.get()
#         for name in all_lookups:
#             if name in env:
#                 value = env[name]
#                 break
#         else:
#             if default is not NOTHING:
#                 value = default
#             else:
#                 raise MissingVariable()

#     return attrs.Factory(_lookup_from_env_vars, takes_self=True)


_ENV_LOOKUPS_KEY = "__pelorus_config_env_lookups"


def field_env_lookups(field: Attribute) -> Sequence[str]:
    """
    Gets the list of environment variable names to look up for this field.
    Will default to the field name in uppercase.  If disabled, will return an empty sequence.
    """
    field_name = field.name

    if _ENV_LOOKUPS_KEY not in field.metadata:
        # default to the variable's name in uppercase.
        return [field_name.upper()]

    env_lookups: Optional[Sequence[str]] = field.metadata[_ENV_LOOKUPS_KEY]

    # if None or an empty sequence, env_lookups are not desired.
    return env_lookups if env_lookups is not None else tuple()


ConfigClass = TypeVar("ConfigClass")


@attrs.define
class EnvironmentConfigLoader(Generic[ConfigClass]):
    """
    Construct a config class (decorated with @config) using values from env vars.
    Will also mark where the resulting value came from in `__value_sources` in the instance.

    Not meant to be reused. Create a new ConfigLoader instance each time.
    """

    cls: Type[ConfigClass]
    other: dict[str, Any]
    env: Mapping[str, str]
    kwargs: NothingDict = attrs.field(init=False, factory=NothingDict)
    missing: list[MissingDataError] = attrs.field(init=False, factory=list)
    value_sources: NothingDict = attrs.field(init=False, factory=NothingDict)

    def _all_matches(self, lookups: Sequence[str]):
        """
        Yield all name-value pairs that were present in the mapping.
        """
        for name in lookups:
            if name in self.env:
                yield (name, self.env[name])

    def _load_field(
        self, field: Attribute
    ) -> tuple[Union[Any, Literal[NOTHING]], Union[Any, Literal[NOTHING]]]:
        """
        Tries to load the value for the given field.
        Returns a tuple of the value and the source of the value (for logging).
        Either may be `NOTHING`:
        the value if it's a default from the class definition,
        or the source if it's passed in through `other`.

        Will raise an error if the value is not found but should be.
        """
        name = field.name
        env_lookups = field_env_lookups(field)
        if not env_lookups:
            # deliberately given an empty list or None,
            # meaning this should be provided through `other`.
            if name in self.other:
                return self.other[name], NOTHING
            else:
                raise MissingOther(name)

        for env_name, env_value in self._all_matches(env_lookups):
            if env_value == _DEFAULT_KEYWORD:
                # make sure there is a default configured in the first place.
                # otherwise this will fail when the class is set up.
                if field.default is NOTHING:
                    raise MissingDefault(name, env_name)
                # else attrs has a default, so we don't need to set it.
                # still mark that it came from the default.
                return NOTHING, f"default value ({env_name} set to {env_value})"
            else:
                return env_value, f"from env var {env_name}"

        # nothing found in env, nothing found in other. Only okay if it has a default.
        if field.default is NOTHING:
            raise MissingVariable(name, env_lookups)
        else:
            # make source message more helpful
            if len(env_lookups) == 1:
                return NOTHING, f"default value; {env_lookups[0]} was not set"
            else:
                return (
                    NOTHING,
                    "default value; none of " + ", ".join(env_lookups) + " were set",
                )

    def construct(self) -> ConfigClass:
        """
        Construct an instance of `cls` using the set environment and `other`.
        """
        for field in fields(self.cls):
            name = field.name
            try:
                self.kwargs[name], self.value_sources[name] = self._load_field(field)
            except MissingDataError as e:
                self.missing.append(e)

        if self.missing:
            raise MissingConfigDataError(self.cls.__name__, self.missing)

        instance = self.cls(**self.kwargs)
        setattr(instance, _PELORUS_CONFIG_VALUE_SOURCES, self.value_sources)  # type: ignore

        return instance


__all__ = ["field_env_lookups", "EnvironmentConfigLoader"]
