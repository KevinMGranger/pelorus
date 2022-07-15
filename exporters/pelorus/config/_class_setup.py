from functools import partial
from typing import Optional

import attrs
import attrs.converters
from attrs import Attribute

from pelorus.config.logging import values

from .converters import _converter_for


def __str__(self):
    """
    Standardized __str__ for config classes.
    """
    return type(self).__name__ + "\n" + "\n".join(values(self))


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


def _set_up_converter(attr: Attribute) -> Attribute:
    """
    Sets the converter based on the annotated type, unless one is already given.
    """
    assert attr.type is not None

    if attr.type in (str, Optional[str]):
        return attr

    converter = _converter_for(attr.type)

    # TODO: okay if not loaded from env.
    if converter is None:
        raise TypeError(
            f"Attribute {attr.name} had type {attr.type}, but no converter could be found for it."
        )

    return attr.evolve(converter=converter)


def _hook(cls: type, fields: list[attrs.Attribute]) -> list[attrs.Attribute]:
    """
    Sets up a config class right before attrs finishes setting it up itself.

    1. Creates __str__ (if not defined by the user), protecting sensitive info.
    2. Sets up default converters.
    """
    if not _str_method_is_user_defined(cls):
        cls.__str__ = __str__  # type: ignore

    return [_set_up_converter(field) for field in fields]


config = partial(attrs.define, field_transformer=_hook, str=False, auto_attribs=True)
