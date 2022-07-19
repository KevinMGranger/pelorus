"""
A quick test meant to be manually run for verification.
Will be turned into more fully-fledged tests later.
"""

from typing import Optional

import attrs.converters
from attrs import field

from pelorus.config import load_and_log, var
from pelorus.config._class_setup import config


@config
class ExampleCommittimeConfig:
    foo: str = var()
    kube_client: object = var(env_lookups=None, log=None)
    api_user: Optional[str] = var(
        default=None, env_lookups=["API_USER", "GIT_USER", "GITHUB_USER", "USER"]
    )

    git_api: str = var(default="", env_lookups=["GIT_API", "GITHUB_API"])
    git_provider: str = "github"

    tls_verify: bool = field(default=True, converter=attrs.converters.to_bool)

    namespaces: set[str] = var(factory=set)


_ = load_and_log(ExampleCommittimeConfig, other=dict(kube_client=object()))
