from typing import Optional
from pelorus.config import config as pelorus_config
from pelorus.config import load_from_env, var


def test_loading_simple_string():
    @pelorus_config
    class SimpleCase:
        unannotated: str
        with_var: str = var()

    env = dict(UNANNOTATED="unannotated", WITH_VAR="with_var")

    loaded = load_from_env(SimpleCase, env=env)

    assert loaded.unannotated == env["UNANNOTATED"]
    assert loaded.with_var == env["WITH_VAR"]


def test_default():
    @pelorus_config
    class Default:
        foo: str = var(default="foo")
        bar: str = "default from literal"
        baz: Optional[str] = None

    loaded = load_from_env(Default, env=dict())

    assert loaded.foo == "foo"
    assert loaded.bar == "default from literal"
    assert loaded.baz is None


def test_fallback_lookups():
    @pelorus_config
    class Fallback:
        foo: str = var(env_lookups="FOO BAR BAZ".split())

    env = dict(BAR="bar", BAZ="baz")

    loaded = load_from_env(Fallback, env=env)

    assert loaded.foo == env["BAR"]


def test_load_collections():
    @pelorus_config
    class Collections:
        a_set: set[str]
        a_tuple: list[str]
        a_list: list[str]

    expected_list = ["one", "two", "three"]
    expected_tuple = ("one", "two", "three")
    expected_set = {"one", "two", "three"}

    env = dict(
        A_SET="one,two,three,one", A_LIST="one,two,three", A_TUPLE="one,two,three"
    )

    loaded = load_from_env(Collections, env=env)

    assert loaded.a_set == expected_set
    assert loaded.a_tuple == expected_tuple
    assert loaded.a_list == expected_list


def test_loading_from_other():
    @pelorus_config
    class OtherConfig:
        foo: object = var(env_lookups=None)

    foo = object()

    loaded = load_from_env(OtherConfig, other=dict(foo=foo))

    assert loaded.foo is foo
