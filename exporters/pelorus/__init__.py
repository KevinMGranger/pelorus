import logging
import os
from datetime import datetime, timezone
from typing import Optional, Sequence

from kubernetes import config
from prometheus_client.registry import Collector

from . import utils

DEFAULT_APP_LABEL = "app.kubernetes.io/name"
DEFAULT_PROD_LABEL = ""
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "%(asctime)-15s %(levelname)-8s %(message)s"
DEFAULT_LOG_DATE_FORMAT = "%m-%d-%Y %H:%M:%S"
DEFAULT_GIT = "github"
DEFAULT_TLS_VERIFY = "True"
DEFAULT_TRACKER = "jira"
DEFAULT_TRACKER_APP_LABEL = "unknown"
DEFAULT_TRACKER_APP_FIELD = "u_application"


# region: logging setup
def _set_up_logging():
    loglevel = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    numeric_level = getattr(logging, loglevel, None)
    if not isinstance(numeric_level, int):
        raise ValueError("Invalid log level: %s", loglevel)
    root_logger = logging.getLogger()

    formatter = logging.Formatter(
        fmt=DEFAULT_LOG_FORMAT, datefmt=DEFAULT_LOG_DATE_FORMAT
    )
    utils.specialize_debug(formatter)

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger.addHandler(handler)
    root_logger.setLevel(numeric_level)

    print(f"Initializing Logger with LogLevel: {loglevel}")


_set_up_logging()


def print_version(collector_type: str):
    """
    Print the version of the currently running collector.
    Gets this information from environment variables set by an S2I build.
    """
    repo, ref, commit = (
        os.environ.get(f"OPENSHIFT_BUILD_{var.upper()}")
        for var in "source reference commit".split()
    )
    if repo and ref and commit:
        print(
            f"Running {collector_type} exporter from {repo}, ref {ref} (commit {commit})"
        )
    else:
        print(f"Running {collector_type} exporter. No version information found.")


# endregion

# A NamespaceSpec lists namespaces to restrict the search to.
# Use None or an empty list to include all namespaces.
NamespaceSpec = Optional[Sequence[str]]


def load_kube_config():
    if "OPENSHIFT_BUILD_NAME" in os.environ:
        config.load_incluster_config()
        file_namespace = open(
            "/run/secrets/kubernetes.io/serviceaccount/namespace", "r"
        )
        if file_namespace.mode == "r":
            namespace = file_namespace.read()
            print("namespace: %s\n" % (namespace))
    else:
        config.load_kube_config()


def convert_date_time_to_timestamp(date_time, format_string="%Y-%m-%dT%H:%M:%SZ"):
    timestamp = None
    try:
        if isinstance(date_time, datetime):
            timestamp = date_time
        else:
            timestamp = datetime.strptime(date_time, format_string)
    except ValueError:
        raise
    return timestamp.replace(tzinfo=timezone.utc).timestamp()


def convert_timestamp_to_date_time_str(timestamp, format_string="%Y-%m-%dT%H:%M:%SZ"):
    date_time_str = None
    try:
        date_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        date_time_str = date_time.strftime(format_string)
    except ValueError:
        raise
    return date_time_str


def get_app_label():
    return os.getenv("APP_LABEL", DEFAULT_APP_LABEL)


def get_prod_label():
    return os.getenv("PROD_LABEL", DEFAULT_PROD_LABEL)


def missing_configs(vars):
    missing_configs = False
    for var in vars:
        if var not in os.environ:
            logging.error("Missing required environment variable '%s'." % var)
            missing_configs = True

    return missing_configs


def upgrade_legacy_vars():
    username = os.environ.get("GITHUB_USER")
    token = os.environ.get("GITHUB_TOKEN")
    api = os.environ.get("GITHUB_API")
    if username and not os.getenv("GIT_USER"):
        os.environ["GIT_USER"] = username
    if token and not os.getenv("GIT_TOKEN"):
        os.environ["GIT_TOKEN"] = token
    if api and not os.getenv("GIT_API"):
        os.environ["GIT_API"] = api


def url_joiner(url, path):
    """Join to sections for a URL and add proper forward slashes"""
    url_link = "/".join(s.strip("/") for s in [url, path])
    return url_link


class AbstractPelorusExporter(Collector):
    pass
