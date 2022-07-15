# from typing import Optional

from typing import Optional

import attrs.converters
from attrs import field

from pelorus.config import var
from pelorus.config._class_setup import config
from pelorus.config.loading import load_from_env


@config
class ExampleCommittimeConfig:
    foo: str = var()
    kube_client: object = var(env_lookups=None)
    api_user: Optional[str] = var(
        default=None, env_lookups=["API_USER", "GIT_USER", "GITHUB_USER", "USER"]
    )
    # token: Optional[str] = var(
    #     default=None, env_lookups=["TOKEN", "GIT_TOKEN", "GITHUB_TOKEN"]
    # )

    git_api: str = var(default="", env_lookups="GIT_API GITHUB_API".split())
    git_provider: str = "github"

    tls_verify: bool = field(default=True, converter=attrs.converters.to_bool)

    namespaces: set[str] = var(factory=set)


x = load_from_env(ExampleCommittimeConfig, other=dict(kube_client=object()))

print("here's a", x)
