import pytest
from attrs import define, field
from cattrs import ClassValidationError, Converter

from pelorus.structure import nested, set_up_converter

# TODO: test inheritance

# TODO: pytest fixture or setup step
converter = Converter()
set_up_converter(converter)


def test_simple_positive():
    @define
    class Simple:
        str_: str
        int_: int

    converter.structure(dict(str_="str", int_=2), Simple)


def test_simple_type_err():
    @define
    class Int:
        int_: int

    with pytest.raises(ClassValidationError) as e:
        converter.structure(dict(int_="string!"), Int)
    assert e.value.subgroup(lambda e: isinstance(e, TypeError)) is not None


def test_simple_absence():
    @define
    class Missing:
        str_: str

    with pytest.raises(ClassValidationError) as e:
        converter.structure(dict(), Missing)

    assert e.value.subgroup(lambda e: isinstance(e, KeyError)) is not None


def test_nested_classes_positive():
    @define
    class Inner:
        str_: str

    @define
    class Outer:
        inner: Inner
        int_: int

    converter.structure(dict(int_=2, inner=dict(str_="str")), Outer)


def test_nested_field_positive():
    @define
    class Nested:
        nested_int: int = field(metadata=nested("foo.bar"))

    converter.structure(dict(foo=dict(bar=2)), Nested)


def test_nested_field_type_err():
    @define
    class Nested:
        nested_int: int = field(metadata=nested("foo.bar"))

    with pytest.raises(ClassValidationError) as e:
        converter.structure(dict(foo=dict(bar="string!")), Nested)

    assert e.value.subgroup(lambda e: isinstance(e, TypeError)) is not None


@pytest.mark.xfail(reason="defaults not implemented yet")
def test_default():
    @define
    class Default:
        str_with_default_: str = "default"

    x = converter.structure(dict(), Default)

    assert x.str_with_default_ == "default"
