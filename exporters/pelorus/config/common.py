from dataclasses import MISSING
from typing import Any, Literal, Mapping, Type, TypeVar, Union, cast

MetadataType = TypeVar("MetadataType")


def _get_metadata_value(
    metadata: Mapping[str, Any],
    key: str,
    type_: Type[MetadataType],
) -> Union[MetadataType, Literal[MISSING]]:
    """
    Get the metadata with the given key.
    A missing value will always return `MISSING`, and the type will be cast.

    Without this, `key in metadata` will be true even if it falls back to the
    sentinel value of `MISSING`.
    """
    value = metadata.get(key, MISSING)
    if value is not MISSING:
        return cast(type_, value)
    else:
        return value
