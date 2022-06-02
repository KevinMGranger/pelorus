from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Iterable, NamedTuple, Optional, cast

from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import Collector
from requests import Session

import pelorus
from pelorus.utils import TokenAuth, join_url_path_components
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
            labels=["namespace", "app", "image_sha", "release_tag"],
        )

        for project in self._projects:
            namespace, app = project.split("/")
            releases = set(self._get_releases_for_project(project))
            commits = self._get_each_tag_commit(
                project, set(release.tag_name for release in releases)
            )

            for release in releases:
                if commit := commits.get(release.tag_name):
                    metric.add_metric(
                        [namespace, app, commit, release.tag_name],
                        release.published_at.timestamp(),
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

    def _get_each_tag_commit(self, project: str, tags: set[str]) -> dict[str, str]:
        """
        Gets the linked commit for every tag given.
        Returns a dictionary where the key is the tag name,
        and the value is the commit hash.

        The tag will not be present in the dict if the tag was not found.

        If one of the following errors occurred, then it will be logged,
        and whatever info that was collected so far will be returned.

        BadAttributePathError if info is missing,
        Any GitHubError from talking to GitHub
        """

        tags_to_commits = {}

        try:
            url = f"https://{self._host}/" + join_url_path_components(
                "repos", project, "tags"
            )
            for tag in paginate_github(self._session, url):
                tag_name = tag["name"]

                if tag_name in tags:
                    tags_to_commits[tag_name] = tag["commit"]["sha"]
        except GitHubError as e:
            logging.error(
                "Error talking to GitHub while getting tags for project %s: %s",
                project,
                e,
                exc_info=True,
            )

        return tags_to_commits


def make_collector():
    custom_host = pelorus.utils.get_env_var("SERVER", "")
    token = pelorus.utils.get_env_var("TOKEN")

    projects = pelorus.utils.get_env_var("PROJECTS", "")
    projects = re.sub(r"\s", ",", projects)
    projects = projects.split(",")
    if not projects:
        raise ValueError("No projects specified for GitHub deploytime collector")

    return GitHubReleaseCollector(projects, custom_host, token)
