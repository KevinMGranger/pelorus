"""
Type stubs to make working with openshift objects a little easier.
These are not meant to be "real" types. Instead, you can claim
that untyped, dynamic data from openshift "fits" these shapes.

These should probably be type stubs only, but I can't figure
out how to do that yet.
"""
from typing import Generic, TypeVar

import attrs


@attrs.define
class Metadata:
    """
    OpenShift metadata. Almost always guaranteed to be present.
    """

    name: str
    namespace: str
    labels: dict[str, str]
    annotations: dict[str, str]


@attrs.define
class CommonResourceInstance:
    "Resource instances that we work with usually have the typical metadata."
    apiVersion: str
    kind: str
    metadata: Metadata


R = TypeVar("R", bound=CommonResourceInstance)


@attrs.define
class CommonResourceInstanceList(CommonResourceInstance, Generic[R]):
    "We work with lists a lot. This lets us easily mark what they contain."
    items: list[R]


@attrs.define
class Build(CommonResourceInstance):
    @attrs.define
    class Output:
        @attrs.define
        class To:
            pass

    # spec: BuildSpec


# __all__ = [
#     "Metadata",
#     "CommonResourceInstance",
#     "CommonResourceInstanceList",
# ]
