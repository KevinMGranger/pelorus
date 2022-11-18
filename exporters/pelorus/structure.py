"""
Declarative structuring and typechecking.

Useful for checking that all necessary aspects of a structure from OpenShift are present and correct.

TODO: add default support
TODO: do we handle defaults on any BadAttribute error?
      or just lop off one side and check for its absence in the last part?
      I think we can just inspect that exception since it has the slice of the path.
"""
from typing import Any, Optional, TypeVar, cast

import attr
import attrs
import cattrs

from pelorus.utils import get_nested

# metadata
_NESTED_PATH_KEY = "__pelorus_structure_nested_path"

A = TypeVar("A", bound="attr.AttrsInstance")
T = TypeVar("T")


def nested(path: str) -> dict[str, Any]:
    "Put the nested data path in a metadata dict."
    return {_NESTED_PATH_KEY: path}


def _is_attrs_class(cls: type) -> Optional[type["attr.AttrsInstance"]]:
    """
    Return the class if it is an attrs class, else None.

    This exists because `attrs.has` is not a proper TypeGuard.
    """
    return cast("type[attr.AttrsInstance]", cls) if attrs.has(cls) else None


def _type_check(src: Any, target: type[T]) -> T:
    "Raise a TypeError if src is not an instance of the target type."
    if not isinstance(src, target):
        raise TypeError(
            f"Required a {target.__name__}, but got an instance of {type(src)}: {src}"
        )
    else:
        return src


# TODO: why does this not work when just registering?
def _register_primitive_type_checks(conv: cattrs.Converter):
    "Register structure hooks for some standard primitives (int, float, str, bool)"
    for type_ in [int, float, str, bool]:
        conv.register_structure_hook(type_, _type_check)


# TODO: yeah, this should still be a cattrs hook. Gotta file that issue.
def _handle_attrs_class(src: dict[str, Any], cls_: type[A]) -> A:
    "Initialize an attrs class field-by-field, handling nested fields properly."
    cls = _is_attrs_class(cls_)
    assert cls is not None

    field_errors = []
    class_kwargs = {}

    field: attrs.Attribute
    for field in attrs.fields(cls):
        field_type = field.type
        assert isinstance(field_type, type)

        nested: Optional[str] = field.metadata.get(_NESTED_PATH_KEY)

        try:
            value = get_nested(src, nested) if nested else src[field.name]
            for primitive in [int, float, str, bool]:
                if issubclass(field_type, primitive):
                    value = _type_check(value, field_type)
                    break

            class_kwargs[field.name] = cattrs.structure(value, field_type)
        except Exception as e:
            field_errors.append(e)

    if not field_errors:
        return cls(**class_kwargs)  # type: ignore
    else:
        raise cattrs.ClassValidationError(
            f"While structuring {cls.__name__}", field_errors, cls
        )


def set_up_converter(conv: cattrs.Converter):
    "Set the given converter to type check and handle attrs classes with nested attributes."
    _register_primitive_type_checks(conv)
    conv.register_structure_hook_func(attrs.has, _handle_attrs_class)
