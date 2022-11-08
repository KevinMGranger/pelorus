"""
Type stubs to make working with openshift objects a little easier.
"""
from typing import Any, Generic, TypeVar

from openshift.dynamic.client import DynamicClient


class ResourceInstance:
    client: DynamicClient

    def __getattribute__(self, __name: str) -> Any:
        ...


class Metadata:
    name: str
    labels: dict[str, str]
    annotations: dict[str, str]


class CommonResource(ResourceInstance):
    apiVersion: str
    kind: str
    metadata: Metadata


R = TypeVar("R", bound=CommonResource)


class ResourceInstanceList(CommonResource, Generic[R]):
    items: list[R]


__all__ = ["ResourceInstance", "Metadata", "CommonResource", "ResourceInstanceList"]
