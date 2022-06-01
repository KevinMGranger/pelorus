from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Iterable, NamedTuple, Optional

from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import Collector
from requests import Session

from pelorus.utils import join_url_path_components


class Release(NamedTuple):
    tag_name: str
    published_at: datetime

    @classmethod
    def from_json(cls, json_object: dict[str, Any]) -> Release:
        return Release(
            # TODO parse datetime
            tag_name=json_object["tag_name"],
            published_at=json_object["published_at"],
        )


class GitHubReleaseCollector(Collector):
    # TODO: regex to determine which releases are "prod"

    def __init__(self, projects: Iterable[str], custom_host: Optional[str] = None):
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
            for release in self._get_releases_for_project(project):  # type: ignore
                commit = self._get_commit_for_tag(project, release.tag_name)
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
        next_url = f"https://{self._host}" + join_url_path_components(
            "repos", project, "releases"
        )
        response = self._session.get(next_url)
        response.raise_for_status()

        last_url: str = response.links["last"]["url"]

        while True:
            for release in response.json():
                yield Release.from_json(release)

            if next_url == last_url:
                break

            response = self._session.get(next_url)
            response.raise_for_status()

            next_url = response.links["next"]["url"]

    def _get_commit_for_tag(self, project: str, tag_name: str) -> str:
        url = f"https://{self._host}" + join_url_path_components(
            "repos", project, "tags"
        )
        response = self._session.get(url)
        response.raise_for_status()

        for tag in response.json():
            if tag["name"] == tag_name:
                return tag["commit"]["sha"]

        raise ValueError(f"No commit for {tag_name} in {project} found")


def make_collector():
    raise NotImplementedError
