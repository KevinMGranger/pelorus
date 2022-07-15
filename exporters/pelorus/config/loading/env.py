from functools import cached_property
from typing import Any, Literal, Mapping, Optional, Sequence, Union

import attrs
from attr import Attribute

from pelorus.config._attrs_compat import NOTHING
from pelorus.config.common import _DEFAULT_KEYWORD
from pelorus.config.loading.errors import MissingDefault, MissingOther, MissingVariable

_ENV_LOOKUPS = "__pelorus_config_env_lookups"

# TODO: the way we're doing it, "unset" and "DEFAULT" are treated the same if a default is set.
# That's the way get_env_vars currently does it.
# But are we taking away the option to have `Optional[str]`?
# We don't support that right now anyway, but is there a use case for that?
# I'll argue no, since it's impossible to unset a var already set in openshift.
# TODO: now, counting an empty as unset: yes. that's worth doing Optional for.
# We need to discuss that though, since that's not how `get_env_vars` works.


@attrs.define(slots=False)
class ValueFinder:
    """
    A ValueFinder looks for the value described by `field` in the environment `env`.
    """

    field: Attribute
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

        # if None or an empty sequence, env_lookups are not desired.
        return env_lookups if env_lookups is not None else tuple()

    def all_matches(self):
        """
        Yield all name-value pairs that were present in the mapping.
        """
        for name in self.env_lookups:
            if name in self.env:
                yield (name, self.env[name])

    # TODO: whether or not `other` gets passed here, whether or not it gets updated
    # to actually makes the class... gotta be consistent, make it clean.
    # It's nice that all error handling is here, y'know?
    def find(self, other: dict[str, Any]) -> Union[Any, str, Literal[NOTHING]]:
        """
        Attempt to find the value given for this field.
        If present or handled by other, return the value.
        If missing (or set to default) but attrs will handle the default, return NOTHING.

        If missing (or set to default) but attrs _does not_ have a default, raise an error.
        If set to ignore the environment but not present in env_lookups, raise an error.
        """
        # TODO: look at other first?
        # or is that handled elsewhere?
        # TODO: remove other, then.
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
                # make sure there is a default configured in the first place.
                # otherwise this will fail when the class is set up.
                if self.field.default is NOTHING:
                    raise MissingDefault(self.field.name, env_name)
                # else attrs has a default, so we don't need to set it.
                # Give NOTHING to the kwarg dict.
                return NOTHING
            else:
                return env_value

        # nothing found in env, nothing found in other. If optional that's fine but otherwise...
        if self.field.default is NOTHING:
            raise MissingVariable(self.field.name, env_lookups)
        else:
            return NOTHING
