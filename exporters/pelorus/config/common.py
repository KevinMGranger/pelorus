import os
from collections import UserDict
from typing import Literal, MutableMapping, TypeVar, Union

import pelorus.utils

from ._attrs_compat import NOTHING

_DEFAULT_KEYWORD = (
    os.getenv("PELORUS_DEFAULT_KEYWORD") or pelorus.utils.DEFAULT_VAR_KEYWORD
)

K = TypeVar("K")
V = TypeVar("V")


class NothingDict(UserDict, MutableMapping[K, V]):
    """
    A dictionary that treats the value of `NOTHING` as absence.
    `NOTHING` values are still kept internally, but not exposed for any queries.
    For example, setting a key to `NOTHING` will keep that key's presence in the dict,
    but that key will no longer show up for `key in container` checks, etc.
    """

    def __contains__(self, key):
        value = self.data.get(key, NOTHING)
        return value is not NOTHING

    def __getitem__(self, key):
        value = self.data.get(key, NOTHING)
        if value is NOTHING:
            raise KeyError

    def get(self, key, default=None):
        value = self.data.get(key, NOTHING)
        return default if value is NOTHING else value

    def items(self):
        return (
            (key, value) for key, value in self.data.items() if value is not NOTHING
        )

    def keys(self):
        return (key for key, _ in self.items())

    def values(self):
        return (value for _, value in self.items())

    def __iter__(self):
        return self.keys()

    def __len__(self):
        return sum(1 for _ in self)

    def __setitem__(self, key: K, value: Union[V, Literal[NOTHING]]):
        self.data[key] = value

    def pop(self, key, default=NOTHING):
        value = self.data.pop(key, NOTHING)
        if value is not NOTHING:
            return value
        elif default is not NOTHING:
            return default
        else:
            raise KeyError

    def popitem(self):
        while True:
            k, v = self.data.popitem()
            if v is not NOTHING:
                return v
