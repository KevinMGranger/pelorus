from __future__ import annotations

import logging
from typing import Any, Iterable, NamedTuple, Optional, cast

from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import Collector
from requests import Session

from pelorus.utils import (
    BadAttributePathError,
    BadAttributesError,
    collect_bad_attribute_path_error,
    get_nested,
    join_url_path_components,
)
from provider_common.github import GitHubError, paginate_github


class Release(NamedTuple):
    tag_name: str
    published_at: str  # TODO: parse this

    @classmethod
    def from_json(cls, json_object: dict[str, Any]) -> Release:
        errs = []
        kwargs = {}
        for key in "tag_name published_at".split():
            with collect_bad_attribute_path_error(errs):
                kwargs[key] = get_nested(json_object, key)

        if errs:
            raise BadAttributesError(errs)

        return cls(**kwargs)


class GitHubReleaseCollector(Collector):
    # TODO: regex to determine which releases are "prod"

    def __init__(self, projects: Iterable[str], custom_host: str = ""):
        self._projects = set(projects)
        logging.info("Watching projects %s", self._projects)
        self._session = Session()
        self._host = custom_host or "github.com"

    def collect(self) -> Iterable[GaugeMetricFamily]:
        metric = GaugeMetricFamily(
            "deploy_timestamp",
            "Deployment timestamp",
            labels=["namespace", "app", "image_sha"],
        )

        for project in self._projects:
            for release in self._get_releases_for_project(project):
                commit = self._get_commit_for_tag(project, release.tag_name)

                if commit is None:
                    continue

                metric.add_metric(
                    [
                        "TODO what to do with namespace?",
                        project,
                        release.tag_name,
                        commit,
                        "datetime",  # TODO #release.published_at,
                    ],
                    1.0,  # TODO timestamp
                )
                yield metric  # TODO: is this actually how they want us to do it?

    def _get_releases_for_project(self, project: str) -> Iterable[Release]:
        """
        Get all releases for a project.

        If a release is missing necessary data, it won't be yielded, but will be logged.

        Will stop yielding if there is a GitHubError for any of the reasons outlined in paginate_github.
        """

        try:
            first_url = f"https://{self._host}" + join_url_path_components(
                "repos", project, "releases"
            )
            for release in paginate_github(self._session, first_url):
                try:
                    yield Release.from_json(cast(dict[str, Any], release))
                except BadAttributesError as e:
                    logging.error(
                        "Release for %s was missing attributes: %s. Body: %s",
                        project,
                        e,
                        release,
                    )
        except GitHubError as e:
            logging.error(
                "Error while getting GitHub response for project %s: %s",
                project,
                e,
                exc_info=True,
            )

    def _get_commit_for_tag(self, project: str, target_tag_name: str) -> Optional[str]:
        """
        Get the commit for the given tag name.

        Will log errors and return None for the following reasons:

        BadAttributePathError if info is missing,
        Any GitHubError from talking to GitHub
        """
        try:
            url = f"https://{self._host}" + join_url_path_components(
                "repos", project, "tags"
            )
            for tag in paginate_github(self._session, url):
                tag_name = get_nested(tag, "name", default=None)
                if not tag_name:
                    logging.warning(
                        "Tag for project %s was missing name: %s", project, tag
                    )

                if tag_name == target_tag_name:
                    return get_nested(tag, "commit.sha")

            logging.error("No tag %s for project %s found", target_tag_name, project)
        except BadAttributePathError:
            logging.error(
                "Tag %s for project %s was missing commit info",
                target_tag_name,
                project,
            )
        except GitHubError as e:
            logging.error(
                "Error talking to GitHub while looking for tag %s for project %s: %s",
                target_tag_name,
                project,
                e,
            )

        return None


def make_collector():
    custom_host = pelorus.utils.get_env_var("SERVER", "")
    token = pelorus.utils.get_env_var("TOKEN")

    projects = pelorus.utils.get_env_var("PROJECTS", "")
    projects = re.sub(r"\s", ",", projects)
    projects = projects.split(",")
    if not projects:
        raise ValueError("No projects specified for GitHub deploytime collector")

    return GitHubReleaseCollector(projects, custom_host, token)
