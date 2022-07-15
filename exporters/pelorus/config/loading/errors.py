"""
Environment loading errors, meant to be detailed and used in aggregate.
"""
from dataclasses import dataclass
from typing import Collection, Sequence

from pelorus.config.loading.common import _DEFAULT_KEYWORD


class MissingDataError(Exception):
    pass


@dataclass
class MissingVariable(MissingDataError):
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


@dataclass
class MissingDefault(MissingDataError):
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


@dataclass
class MissingOther(MissingDataError):
    """
    A variable had environment lookups disabled, but was not passed in `other`.
    """

    name: str

    def __str__(self):
        return f"{self.name} had environment lookups disabled, but was not passed in to `load`'s `other` dict."


class MissingConfigDataError(Exception):
    """
    Collects all missing env var issues into one error.
    """

    def __init__(self, config_class: str, missing: Collection[MissingDataError]):
        super().__init__()
        self.config_class = config_class
        self.missing = missing

    def __str__(self):
        return f"Config for {self.config_class} is missing data: " + "\n".join(
            str(x) for x in self.missing
        )
