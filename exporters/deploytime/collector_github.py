from __future__ import annotations

import logging
from typing import Any, Iterable, NamedTuple, Optional

from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import Collector
from requests import HTTPError, JSONDecodeError, Session

from pelorus.utils import (
    BadAttributePathError,
    BadAttributesError,
    collect_bad_attribute_path_error,
    get_nested,
    join_url_path_components,
)


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
            try:
                releases = self._get_releases_for_project(project)
            except HTTPError as e:
                logging.error("Error getting releases for project %s: %s", project, e)
                continue

            for release in releases:
                try:
                    commit = self._get_commit_for_tag(project, release.tag_name)
                except (ValueError, HTTPError, BadAttributePathError) as e:
                    logging.error(
                        "Error getting commit for tag %s in project %s: %s",
                        release.tag_name,
                        project,
                        e,
                    )
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

        If a release is missing necessary data,
        it won't be yielded, but will be logged.

        May raise an HTTPError if the reponse from github was bad.
        """
        next_url = f"https://{self._host}" + join_url_path_components(
            "repos", project, "releases"
        )
        response = self._session.get(next_url)
        response.raise_for_status()

        last_url: str = get_nested(response.links, "last.url")

        while True:
            try:
                responses = response.json()
            except JSONDecodeError as e:
                logging.error("Response was not valid json: %s, error %s", response, e)
                break

            for release in responses:
                try:
                    yield Release.from_json(release)
                except BadAttributesError as e:
                    logging.error(
                        "Release for %s was missing attributes: %s. Body: %s",
                        project,
                        e,
                        release,
                    )

            if next_url == last_url:
                break

            response = self._session.get(next_url)
            response.raise_for_status()

            next_url = get_nested(response.links, "next.url")

    def _get_commit_for_tag(self, project: str, tag_name: str) -> str:
        """
        Get the commit for the given tag name.

        Will raise BadAttributePathError if info is missing,
        an HTTPError if the response was bad,
        or a ValueError if the commit wasn't found.
        """
        url = f"https://{self._host}" + join_url_path_components(
            "repos", project, "tags"
        )
        response = self._session.get(url)
        response.raise_for_status()

        for tag in response.json():
            if get_nested(tag, "name") == tag_name:
                return get_nested(tag, "commit.sha")

        raise ValueError(f"No commit for {tag_name} in {project} found")


def make_collector():
    raise NotImplementedError
