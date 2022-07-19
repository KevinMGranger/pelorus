"""
Config class setup functions.
"""
from functools import partial
from typing import Optional

import attrs
import attrs.converters
from attrs import Attribute

from pelorus.config.loading.env import field_env_lookups
from pelorus.config.logging import format_values

from .converters import _converter_for


def __str__(self):
    """
    Standardized __str__ for config classes.
    """
    config_name = type(self).__name__
    return config_name + "\n" + "\n".join(format_values(self))


def _str_method_is_user_defined(cls: type) -> bool:
    """
    Was the __str__ method defined by the user, or is it the default from object?
    """
    if type(cls) is not type:
        raise Exception(
            "Only regular classes are allowed (this is using a custom metaclass)"
        )

    classes_to_check = cls.__mro__[:-1]  # ignoring last (`object`)

    return any("__str__" in c.__dict__ for c in classes_to_check)


def _set_up_converter(field: Attribute) -> Attribute:
    """
    Sets the converter based on the annotated type, unless one is already given.
    """

    if field.converter is not None:
        return field

    assert field.type is not None

    if field.type in (str, Optional[str]):
        return field

    converter = _converter_for(field.type)

    if converter is None and field_env_lookups(field):
        raise TypeError(
            f"Attribute {field.name} had type {field.type}, but no converter could be found for it."
        )

    return field.evolve(converter=converter)


def _hook(cls: type, fields: list[attrs.Attribute]) -> list[attrs.Attribute]:
    """
    Sets up a config class right before attrs finishes setting it up itself.

    1. Creates __str__ (if not defined by the user), protecting sensitive info.
    2. Sets up default converters.
    """
    if not _str_method_is_user_defined(cls):
        cls.__str__ = __str__  # type: ignore

    return [_set_up_converter(field) for field in fields]


_CONFIG_KWARGS = dict(field_transformer=_hook, str=False, auto_attribs=True)

config = partial(attrs.define, **_CONFIG_KWARGS)
