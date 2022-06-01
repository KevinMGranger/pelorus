from __future__ import annotations

import logging
from datetime import datetime
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
from provider_common.github import GitHubError, paginate_github, parse_datetime


class Release(NamedTuple):
    tag_name: str
    published_at: datetime

    @classmethod
    def from_json(cls, json_object: dict[str, Any]) -> Release:
        tag_name = json_object["tag_name"]
        published_at = parse_datetime(json_object["published_at"])

        return Release(tag_name, published_at)


class GitHubReleaseCollector(Collector):
    # TODO: regex to determine which releases are "prod"?

    def __init__(
        self,
        projects: Iterable[str],
        custom_host: str = "",
        apikey: Optional[str] = None,
    ):
        self._projects = set(projects)
        logging.info("Watching projects %s", self._projects)
        self._session = Session()
        self._host = custom_host or "api.github.com"

        if apikey:
            self._session.auth = TokenAuth(apikey)

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
        yield metric

    def _get_releases_for_project(self, project: str) -> Iterable[Release]:
        """
        Get all releases for a project.

        If a release is missing necessary data, it won't be yielded, but will be logged.

        Will stop yielding if there is a GitHubError for any of the reasons outlined in paginate_github.
        """

        try:
            first_url = f"https://{self._host}/" + join_url_path_components(
                "repos", project, "releases"
            )
            for release in paginate_github(self._session, first_url):
                release = cast(dict[str, Any], release)
                if release["draft"]:
                    continue
                yield Release.from_json(release)
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
            url = f"https://{self._host}/" + join_url_path_components(
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
