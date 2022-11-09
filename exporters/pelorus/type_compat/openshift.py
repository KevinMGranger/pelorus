"""
Type stubs to make working with openshift objects a little easier.
These are not meant to be "real" types. Instead, you can claim
that untyped, dynamic data from openshift "fits" these shapes.

These should probably be type stubs only, but I can't figure
out how to do that yet.
"""
from typing import Any, Generic, TypeVar

from openshift.dynamic.client import DynamicClient


class ResourceInstance:
    """
    A resource as returned by the openshift library.

    `client` highlights that it still references the client,
    and the `__getattribute__ -> Any` makes the type checker
    not complain about attribute accesses.
    """

    client: DynamicClient

    def __getattribute__(self, __name: str) -> Any:
        ...


class Metadata:
    """
    OpenShift metadata. Almost always guaranteed to be present.
    """

    name: str
    labels: dict[str, str]
    annotations: dict[str, str]


class CommonResourceInstance(ResourceInstance):
    "Resource instances that we work with usually have the typical metadata."
    apiVersion: str
    kind: str
    metadata: Metadata


R = TypeVar("R", bound=CommonResourceInstance)


class CommonResourceInstanceList(CommonResourceInstance, Generic[R]):
    "We work with lists a lot. This lets us easily mark what they contain."
    items: list[R]


__all__ = [
    "ResourceInstance",
    "Metadata",
    "CommonResourceInstance",
    "CommonResourceInstanceList",
]
