from dataclasses import dataclass
from itertools import chain
from typing import Iterable, Iterator
from urllib.error import HTTPError

import requests

from pelorus.utils import BadAttributePathError, get_nested


def _validate_github_response(response: requests.Response) -> list:
    """
    Validates that the response from github:
    - was a 2xx response
    - was valid JSON
    - was a list

    This is done separately to avoid duplication in pagination code.

    Returns the list.

    Exceptions:
    HTTPError if there's a bad response
    JSONDecodeError if there's a response with invalid JSON
    ValueError if a response was valid json but wasn't a list
    """
    response.raise_for_status()
    json = response.json()
    if not isinstance(json, list):
        raise ValueError(f"Returned json was not a list: {json}")

    return json


@dataclass
class GitHubError(Exception):
    response: requests.Response
    message: str = "Bad response from GitHub"


@dataclass(slots=True)
class GitHubPageResponse:
    items: list
    response: requests.Response

    def __iter__(self) -> Iterator[list]:
        return iter(self.items)


# TODO: rate limiting
def paginate_github_with_page(
    session: requests.Session, start_url: str
) -> Iterable[GitHubPageResponse]:
    """
    Paginate github requests the way their API dictates:
    https://docs.github.com/en/rest/guides/traversing-with-pagination

    Will return a GitHubError with any of the following set to the __cause__ if they occur:
    HTTPError if there's a bad response
    JSONDecodeError if there's a response with invalid JSON
    ValueError if a response was valid json but wasn't a list
    BadAttributePathError if a response was missing a `next` link or the first was missing a `last` link.

    Yields lists and the response they came from. You will probably want to flatten them.
    """
    response = session.get(start_url)
    try:
        json = _validate_github_response(response)

        last_url: str = get_nested(response.links, "last.url")

        url = start_url

        while True:
            yield GitHubPageResponse(json, response)

            if url == last_url:
                break

            url = get_nested(response.links, "next.url")
            response = session.get(url)
            json = _validate_github_response(response)
    except (HTTPError, requests.JSONDecodeError, ValueError, BadAttributePathError):
        raise GitHubError(response)


def paginate_github(session: requests.Session, start_url: str) -> Iterable:
    return chain.from_iterable(paginate_github_with_page(session, start_url))
