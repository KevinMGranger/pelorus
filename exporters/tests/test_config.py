from dataclasses import dataclass, field
from typing import Optional

from pelorus.config import NoEnv, var


@dataclass
class ExampleCommittimeConfig:
    kube_client: object = var(env_lookups=NoEnv)
    api_user: Optional[str] = var(
        default=None, env_lookups=["API_USER", "GIT_USER", "GITHUB_USER", "USER"]
    )
    token: Optional[str] = var(
        default=None, env_lookups=["TOKEN", "GIT_TOKEN", "GITHUB_TOKEN"]
    )

    git_api: str = var(default="", env_lookups="GIT_API GITHUB_API".split())
    git_provider: str = "github"

    tls_verify: bool = True

    namespaces: set[str] = field(default_factory=set)
