from typing import Optional

import attrs

from pelorus.config import config as pelorus_config
from pelorus.config import load_from_env, var


def test_loading_simple_string():
    @pelorus_config
    class SimpleCase:
        unannotated: str
        with_var: str = var()
        field_works: str = attrs.field()  # type: ignore # FIXME: why does pyright complain here?

    env = dict(UNANNOTATED="unannotated", WITH_VAR="with_var", FIELD_WORKS="field")

    loaded = load_from_env(SimpleCase, env=env)

    assert loaded.unannotated == env["UNANNOTATED"]
    assert loaded.with_var == env["WITH_VAR"]
    assert loaded.field_works == env["FIELD_WORKS"]


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
        a_tuple: tuple[str]
        a_list: list[str]
        default_list: list[str] = var(factory=list)

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
    assert loaded.default_list == []


def test_loading_from_other():
    @pelorus_config
    class OtherConfig:
        foo: object = var(env_lookups=None)

    foo = object()

    loaded = load_from_env(OtherConfig, other=dict(foo=foo))

    assert loaded.foo is foo


def test_logging():
    @pelorus_config
    class Loggable:
        regular_field: str = var(default="LOG ME 1")

        sensitive_credential: str = var(default="REDACT ME 1")
        log_this_credential_anyway: str = var(default="LOG ME 2", log=True)
        explicitly_sensitive: str = var(default="REDACT ME 2", log=False)

        _private_field: str = var(default="SHOULD BE ABSENT 1")
        _private_but_log_me_anyway: str = var(default="LOG ME 3", log=True)
        _private_but_redact_me: str = var(default="REDACT ME 3", log=False)
        not_private_but_skip_logging: str = var(default="SHOULD BE ABSENT 2", log=None)

        from_multi_env: str = var(
            default="", env_lookups=["MULTI_ENV", "FROM_MULTI_ENV"]
        )
        default_name: str = var(default="LOG ME 4")

    instance = load_from_env(Loggable, env=dict(DEFAULT_NAME="default"))

    logged = str(instance)

    print(logged)

    assert "REDACT ME" not in logged
    assert "SHOULD BE ABSENT" not in logged
    for i in range(1, 5):
        assert f"LOG ME {i}" in logged
