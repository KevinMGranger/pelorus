# uber simplified approach: just work with attrs directly, no hooks even.
# metadata is manual because it's the less common case.
# converters are manual.
# stuff is still loaded by inspecting it, but we assemble a fancy dict with our own metadata attached to the values.
# we then log at the end, _intermingling_ what was successful and what was an error*.

# *well, maybe we don't want to handle defaults on our own. or maybe we do!
# we'd just check for and disallow takes_self factories.

# this is easy enough that this could be entirely functions, not a class that handles this.

# adapting this to a yaml / nested based approach is easy as well.

# maybe we do keep the EnvVar default thing. But transforming that requires a hook.
# No, don't do that. The class should live in python-space. That it works with env vars
# is an extension that should remain separate.

import enum
import os
from typing import (
    Any,
    Literal,
    Mapping,
    NamedTuple,
    Protocol,
    Sequence,
    Type,
    TypeVar,
    Union,
    overload,
    Optional,
)
import attrs
from attrs import Attribute, frozen, define
from ._attrs_compat import NOTHING, Factory
from .loading.env import _ENV_LOOKUPS_KEY
from .loading._errors import (
    MissingDataError,
    MissingVariable,
    MissingDefault,
    MissingOther,
)

_SHOULD_LOG = "__pelorus_config_log"

REDACT_WORDS = {"pass", "token", "key", "cred", "secret"}
"""
Variables containing these words are not logged by default, nor are attributes starting with an underscore.
"""


class Log(enum.Enum):
    LOG = enum.auto()
    REDACT = enum.auto()
    SKIP = enum.auto()


class EnvVarWithSource:
    value: Any
    log: Log

    def source(self) -> str:
        ...


@define
class FoundEnvVar(EnvVarWithSource):
    "Found it in an env var"
    env_name: str
    value: str
    log: Log = Log.REDACT

    def source(self):
        return f"from env var {self.env_name}"


@define
class UnsetEnvVar(EnvVarWithSource):
    "No env var, came from attrs"
    value: Any
    env_lookups: tuple[str]
    log: Log = Log.REDACT

    def source(self):
        if len(self.env_lookups) == 1:
            return f"default value; {self.env_lookups[0]} was not set"
        else:
            return "default value; none of " + ", ".join(self.env_lookups) + " were set"


@define
class DefaultSetEnvVar(EnvVarWithSource):
    "Env var was set to default keyword"
    env_name: str
    value: str
    default_keyword: str

    log: Log = Log.REDACT

    def source(self):
        return f"default value ({self.env_name} set to {self.default_keyword})"


def env_vars(*lookups: str) -> dict[str, Any]:
    return {_ENV_LOOKUPS_KEY: lookups}


def no_env_vars() -> dict[str, Any]:
    return {_ENV_LOOKUPS_KEY: tuple()}


def log(should: Log) -> dict[str, Any]:
    return {_SHOULD_LOG: should}


def _should_log(field: Attribute) -> Log:
    """
    A field should NOT be logged if it explicitly marked as such,
    or contains a word that implies it is sensitive (members of REDACT_WORDS).
    """
    should_log = field.metadata.get(_SHOULD_LOG, None)
    if should_log is None:
        is_private = field.name.startswith("_")
        if is_private:
            return Log.SKIP

        should_be_redacted = any(word in field.name.lower() for word in REDACT_WORDS)
        if should_be_redacted:
            return Log.REDACT

        return Log.LOG
    else:
        return should_log


# TODO: bring converters over


@frozen
class EnvFinder:
    "Load from environment or get default"
    field: Attribute
    env: Mapping[str, str]
    env_lookups: tuple[str]
    default_keyword: str

    @property
    def name(self):
        return self.field.name

    def _first_env_match(self) -> Optional[str]:
        "returns the _name_ of the match, not the value"
        for name in self.env_lookups:
            if name in self.env:
                return name
        return None

    def _get_default(self) -> Union[Any, Literal[NOTHING]]:
        default = self.field.default
        if isinstance(default, Factory):
            if default.takes_self:
                raise ValueError(
                    "Factories used for config loading cannot use takes_self"
                )
            return default.factory()  # type: ignore
        else:
            return default

    def _value_or_default(self) -> Union[EnvVarWithSource, MissingDataError]:
        env_name = self._first_env_match()

        if env_name is None:
            value = self._get_default()
            if value is NOTHING:
                return MissingVariable(self.name, self.env_lookups)
            else:
                return UnsetEnvVar(value, self.env_lookups)

        value = self.env[env_name]
        if value == self.default_keyword:
            value = self._get_default()
            if value is NOTHING:
                return MissingDefault(self.name, env_name)
            else:
                return DefaultSetEnvVar(env_name, value, self.default_keyword)

        return FoundEnvVar(env_name, value)

    @classmethod
    def get_value(
        cls, field: Attribute, env: Mapping[str, str], default_keyword: str
    ) -> Union[EnvVarWithSource, MissingDataError, Literal[NOTHING]]:
        "Load from env or get default. Returns NOTHING if it should be in `other`"
        if _ENV_LOOKUPS_KEY in field.metadata:
            env_lookups = field.metadata[_ENV_LOOKUPS_KEY]
        else:
            env_lookups = tuple(field.name.upper())

        if not env_lookups:
            # deliberately don't check. needs to be in other
            return NOTHING

        return cls(field, env, env_lookups, default_keyword)._value_or_default()


ConfigClass = TypeVar("ConfigClass")


def load_and_log(
    cls: Type[ConfigClass],
    other: dict[str, Any] = {},
    *,
    env: Mapping[str, str] = os.environ,
    default_keyword: str = "default",
) -> Optional[ConfigClass]:
    results: dict[str, Any] = dict()
    any_errors = False
    for field in attrs.fields(cls):
        name = field.name

        if name in other:
            results[name] = other[name]
            continue

        value = EnvFinder.get_value(field, env, default_keyword)
        if value is NOTHING:
            if name not in other:
                results[name] = MissingOther(name)
            else:
                results[name] = other[name]
        elif isinstance(value, MissingDataError):
            results[name] = value
            any_errors = True
        else:
            value.log = _should_log(field)
            results[name] = value

    if any_errors:
        print(
            f"While loading config {cls.__name__}, errors were encountered. All values:"
        )
    else:
        print(f"Loading {cls.__name__}, inputs below:")

    for field, value in results.items():
        if isinstance(value, EnvVarWithSource):
            if value.log is Log.SKIP:
                continue

            if value.log is Log.REDACT:
                value, source = "REDACTED", value.source()
            else:
                value, source = value.value, value.source()

            print(f"{field}={value}, {source}")
        elif isinstance(value, MissingDataError):
            print(f"{field}=ERROR:", value)
        else:  # came from other, skip logging.
            pass

    if any_errors:
        return None

    kwargs = dict((k, v.value) for k, v in results.items())

    return cls(**kwargs)
