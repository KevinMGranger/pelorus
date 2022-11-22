# Copyright Red Hat
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""
Type stubs to make working with openshift objects a little easier.
These are not meant to be "real" types. Instead, you can claim
that untyped, dynamic data from openshift "fits" these shapes.

These should probably be type stubs only, but I can't figure
out how to do that yet.
"""
from typing import TypeVar

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
