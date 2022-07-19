from pelorus.config import config as pelorus_config
from pelorus.config import load_from_env, var


def test_loading_simple_string():
    @pelorus_config
    class DefaultCase:
        foo: str = var()

    env = dict(FOO="bar")

    loaded = load_from_env(DefaultCase, env=env)

    assert loaded.foo == env["FOO"]
