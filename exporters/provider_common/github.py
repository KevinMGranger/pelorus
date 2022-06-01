import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import chain
from typing import Iterable, Iterator
from urllib.error import HTTPError

import requests

from pelorus.utils import BadAttributePathError, get_nested

# The maximum number of requests you're permitted to make per hour.
RATELIMIT_LIMIT_HEADER = "x-ratelimit-limit"
# The number of requests remaining in the current rate limit window.
RATELIMIT_REMAINING_HEADER = "x-ratelimit-remaining"
# The time at which the current rate limit window resets in UTC epoch seconds.
RATELIMIT_RESET_HEADER = "x-ratelimit-reset"


def _log_ratelimit(response: requests.Response):
    """
    Log ratelimit header values as a debug message,
    or an error if the request failed due to rate limits.
    Will ignore errors getting this information,
    as the info isn't strictly critical.
    """
    try:
        rate_limit = int(response.headers[RATELIMIT_LIMIT_HEADER])
        remaining_requests = int(response.headers[RATELIMIT_REMAINING_HEADER])

        reset_time = response.headers[RATELIMIT_RESET_HEADER]
        reset_time = datetime.fromtimestamp(float(reset_time), timezone.utc)

        if not response.ok and remaining_requests == 0:
            log_level = logging.ERROR
        else:
            log_level = logging.DEBUG

        logging.log(
            log_level,
            "GitHub rate limit headers: %s: %s, %s: %s, %s: %s",
            RATELIMIT_LIMIT_HEADER,
            rate_limit,
            RATELIMIT_REMAINING_HEADER,
            remaining_requests,
            RATELIMIT_RESET_HEADER,
            reset_time,
        )
    except Exception as e:
        logging.error(
            "Issue with github rate limit headers: %s",
            e,
            exc_info=True,
        )


def _validate_github_response(response: requests.Response) -> list:
    """
    Validates that the response from github:
    - was a 2xx response
    - was valid JSON
    - was a list

    This is done separately to avoid duplication in pagination code.

    Will also log rate limit headers as a debug message.
    If the rate limit is exceeded, GitHub will return a 4xx--
    the logging is just for context.

    Returns the list.

    Exceptions:
    HTTPError if there's a bad response
    JSONDecodeError if there's a response with invalid JSON
    ValueError if a response was valid json but wasn't a list
    """
    _log_ratelimit(response)
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


def paginate_github_with_page(
    session: requests.Session, start_url: str
) -> Iterable[GitHubPageResponse]:
    """
    Paginate github requests the way their API dictates:
    https://docs.github.com/en/rest/guides/traversing-with-pagination

    Yields lists and the response they came from. This is solely so you can inspect the response.
    For higher-level usage, use `paginate_github`, which flattens each item in each list for you.

    Will return a GitHubError with any of the following set to the __cause__ if they occur:
    HTTPError if there's a bad response
    JSONDecodeError if there's a response with invalid JSON
    ValueError if a response was valid json but wasn't a list
    BadAttributePathError if a response was missing a `next` link or the first was missing a `last` link.
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
    """
    Paginate github requests the way their API dictates:
    https://docs.github.com/en/rest/guides/traversing-with-pagination

    Will yield each item in each response list, automatically requesting
    subsequent pages as necessary.

    Will return a GitHubError with any of the following set to the __cause__ if they occur:
    HTTPError if there's a bad response
    JSONDecodeError if there's a response with invalid JSON
    ValueError if a response was valid json but wasn't a list
    BadAttributePathError if a response was missing a `next` link or the first was missing a `last` link.
    """
    return chain.from_iterable(paginate_github_with_page(session, start_url))
