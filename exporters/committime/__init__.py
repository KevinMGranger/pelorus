#!/usr/bin/env python3
#
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
#

from __future__ import annotations

from typing import Optional

import attrs
import giturlparse

from pelorus.type_compat.openshift import CommonResourceInstance
from pelorus.utils import collect_bad_attribute_path_error, get_nested

DEFAULT_PROVIDER = "git"
PROVIDER_TYPES = {"git", "image"}
GIT_PROVIDER_TYPES = {"github", "bitbucket", "gitea", "azure-devops", "gitlab"}

SUPPORTED_PROTOCOLS = {"http", "https", "ssh", "git"}


@attrs.frozen
class GitRepo:
    "Extracted information about a git repo url."

    url: str
    """
    The full URL for the repo.
    Obtained from build metadata, Image annotations, etc.
    """
    protocol: str
    fqdn: str
    group: str
    name: str
    "The git repo name, e.g. myrepo.git"
    project: str
    "The git project name. Typically the repo name without `.git`"
    port: Optional[str]

    @property
    def server(self) -> str:
        "The protocol, server FQDN, and port in URL format."
        url = f"{self.protocol}://{self.fqdn}"

        if self.port:
            url += f":{self.port}"

        return url

    @classmethod
    def from_url(cls, url: str):
        "Parse the given URL and handle the edge cases for it."

        # code inherited from old committime metric class.
        # Unsure of the purpose of some of this code.

        # Ensure git URI does not end with "/", issue #590
        url = url.strip("/")
        parsed = giturlparse.parse(url)
        if len(parsed.protocols) > 0 and parsed.protocols[0] not in SUPPORTED_PROTOCOLS:
            raise ValueError("Unsupported protocol %s", parsed.protocols[0])
        protocol = parsed.protocol
        # In the case of multiple subgroups the host will be in the pathname
        # Otherwise, it will be in the resource
        if parsed.pathname.startswith("//"):
            fqdn = parsed.pathname.split("/")[2]
            protocol = parsed.protocols[0]
        else:
            fqdn = parsed.resource
        group = parsed.owner
        name = parsed.name
        project = parsed.name
        port = parsed.port

        return cls(url, protocol, fqdn, group, name, project, port)


@attrs.define
class CommitTimeRetrievalInput:
    """
    Information used to retrieve commit time information.
    Previously, this information wasn't guaranteed to be present,
    which made the code messy with various checks and exceptions, etc.
    Or worse, just hoping things weren't None and we wouldn't crash the exporter.

    In addition, it was unclear how exporters should report the commit time:
    they change it on the metric, but also return the metric,
    but if they return None, it shouldn't be counted... confusing.
    This allows us to handle things more consistently.
    """

    # TODO: add back in optional data for logging context?

    repo: GitRepo
    commit_hash: str

    @property
    def repo_url(self) -> Optional[str]:
        return self.repo.url if self.repo else None

    @repo_url.setter
    def repo_url(self, url: str):
        self.repo = GitRepo.from_url(url)


@attrs.define
class CommitMetric:
    name: str = attrs.field()
    annotations: dict[str, str] = attrs.field(factory=dict, kw_only=True)
    namespace: Optional[str] = attrs.field(default=None, kw_only=True)

    repo: Optional[GitRepo] = attrs.field(default=None, kw_only=True)

    @property
    def repo_url(self) -> Optional[str]:
        return self.repo.url if self.repo else None

    @repo_url.setter
    def repo_url(self, url: str):
        self.repo = GitRepo.from_url(url)

    commit_hash: Optional[str] = attrs.field(default=None, kw_only=True)
    # TODO: combine these
    commit_time: Optional[str] = attrs.field(default=None, kw_only=True)
    """
    A human-readable timestamp.
    In the future, this and commit_timestamp should be combined.
    """
    commit_timestamp: Optional[float] = attrs.field(default=None, kw_only=True)
    """
    The unix timestamp.
    In the future, this and commit_time should be combined.
    """

    build_name: Optional[str] = attrs.field(default=None, kw_only=True)
    "The name of the build this commit metric came from. Only used for logging."

    image_hash: Optional[str] = attrs.field(default=None, kw_only=True)

    # maps attributes to their location in a `Build`.
    #
    # missing attributes or with False argument are handled specially:
    #
    # name: set when the object is constructed
    # repo_url: if it's not present in the Build, fallback logic needs to be handled elsewhere
    # commit_hash: if it's missing in the Build, fallback logic needs to be handled elsewhere
    _BUILD_MAPPING = dict(
        build_name=("metadata.name", True),
        namespace=("metadata.namespace", True),
        image_hash=("status.output.to.imageDigest", True),
        commit_hash=("spec.revision.git.commit", False),
        repo_url=("spec.source.git.uri", False),
    )

    _ANNOTATION_MAPPING = dict(
        repo_url="io.openshift.build.source-location",
        commit_hash="io.openshift.build.commit.id",
        commit_time="io.openshift.build.commit.date",
    )


def commit_metric_from_build(
    app: str, build: CommonResourceInstance, errors: list
) -> CommitMetric:
    """
    Create a CommitMetric from build information.
    Will collect errors for missing data instead of failing early.
    """
    # set attributes based on a mapping from attribute name to
    # lookup path.
    # Collect all errors to be reported at once instead of failing fast.
    metric = CommitMetric(app)
    for attr_name, (path, required) in CommitMetric._BUILD_MAPPING.items():
        with collect_bad_attribute_path_error(errors, required):
            value = get_nested(build, path, name="build")
            setattr(metric, attr_name, value)

    return metric
