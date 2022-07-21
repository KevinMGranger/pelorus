"""
A declarative way to load configuration from environment variables, and log that configuration properly.

See the [README](./README.md) file for documentation.
See [DEVELOPING](./DEVELOPING.md) for implementation details / dev docs.
"""

import logging
import os
from typing import Any, Generic, Mapping, Type, TypeVar

import attrs

from pelorus.config.loading import (
    MissingConfigDataError,
    MissingDataError,
    ValueWithSource,
    _EnvFinder,
)
from pelorus.config.log import REDACT, SKIP

_logger = logging.getLogger(__name__)


def _prepare_kwargs(results: dict[str, Any]):
    """
    Handle the following cases:

    Attrs removes underscores from field names for the init param names,
    so we need to change the field names for the kwargs.

    We wrap values in classes describing where they came from, so we need to unpack those.
    """
    for k, v in results.items():
        if isinstance(v, ValueWithSource):
            value = v.value
        else:
            value = v

        yield k.lstrip("_"), value


ConfigClass = TypeVar("ConfigClass")


@attrs.frozen
class LoggingLoader(Generic[ConfigClass]):
    cls: Type[ConfigClass]
    other: dict[str, Any]
    env: Mapping[str, str]
    default_keyword: str
    logger: logging.Logger

    results: dict[str, Any] = attrs.field(factory=dict, init=False)
    errors: list[MissingDataError] = attrs.field(factory=list, init=False)

    def _load(self):
        for field in attrs.fields(self.cls):
            if not field.init:
                # field does not get set during instance creation,
                # so don't load it.
                continue

            name = field.name

            value = _EnvFinder.get_value(
                field, self.env, self.other, self.default_keyword
            )

            if isinstance(value, MissingDataError):
                self.results[name] = value
                self.errors.append(value)
            else:
                self.results[name] = value

    def _log(self):
        if self.errors:
            log_with_level = self.logger.error
            log_with_level(
                "While loading config %s, errors were encountered. All values:",
                self.cls.__name__,
            )
        else:
            log_with_level = self.logger.info
            log_with_level("Loading %s, inputs below:", self.cls.__name__)

        for field, value in self.results.items():
            if isinstance(value, ValueWithSource):
                if value.log is SKIP:
                    continue

                source = value.source()

                if value.log is REDACT:
                    value = "REDACTED"
                else:
                    value = repr(value.value)

                log_with_level("%s=%s, %s", field, value, source)
            elif isinstance(value, MissingDataError):
                log_with_level("%s=ERROR: %s", field, value)

    def load_and_log(self) -> ConfigClass:
        self._load()
        self._log()

        if self.errors:
            raise MissingConfigDataError(self.cls.__name__, self.errors)

        kwargs = dict(_prepare_kwargs(self.results))

        return self.cls(**kwargs)


def load_and_log(
    cls: Type[ConfigClass],
    other: dict[str, Any] = {},
    *,
    env: Mapping[str, str] = os.environ,
    default_keyword: str = "default",
    logger: logging.Logger = _logger,
) -> ConfigClass:
    loader = LoggingLoader(
        cls, other=other, env=env, default_keyword=default_keyword, logger=logger
    )
    return loader.load_and_log()
