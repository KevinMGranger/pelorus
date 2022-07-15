"""
Converters to augment `attrs.converters`,
and tools to integrate them with our config system.
"""
from collections.abc import Callable, Collection, Iterator
from functools import partial
from typing import Any, Optional, TypeVar, Union

CollectionType = TypeVar("CollectionType", bound=Collection[str])


def comma_separated(
    collection: Callable[[Iterator[str]], CollectionType]
) -> Callable[[Union[str, CollectionType]], CollectionType]:
    """
    Splits a comma-separated string into the given collection,
    stripping whitespace from each element.

    Meant to be partially bound and used as an attrs converter.

    If a string is not given, it is assumed to be the target
    collection type and is returned as-is. (Useful for testing.)
    """
    return partial(_comma_separated_collection, collection)


def _comma_separated_collection(
    collection: Callable[[Iterator[str]], CollectionType],
    val: Union[str, CollectionType],
) -> CollectionType:
    if isinstance(val, str):
        return collection(part.strip() for part in val.split(","))
    else:
        return val


# this isn't a dict because we can rely on type equality, but not hashability.
# Any because `type` doesn't work with something like Optional[str] for some reason?
_TYPE_TO_DEFAULT_CONVERTER: list[tuple[Any, Optional[Callable]]] = [
    (int, int),
    (list[str], comma_separated(list)),
    (set[str], comma_separated(set)),
    (tuple[str], comma_separated(tuple)),
    # TODO: we should either standardize or require explicitness for
    # TODO: this is different behavior than strtobool!
    # Is that a backwards incompatible change?
    # whether or not an empty string is none or bool
    # bool: attrs.converters.to_bool,
]


def _converter_for(type_: type) -> Optional[Callable]:
    """
    Gets the converter for the given type, if any.
    """
    for converter_type, converter in _TYPE_TO_DEFAULT_CONVERTER:
        if type_ == converter_type:
            return converter

    return None


__all__ = ["comma_separated"]
