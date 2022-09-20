from datetime import datetime, timezone
from typing import Union

# https://docs.openshift.com/container-platform/4.10/rest_api/objects/index.html#io.k8s.apimachinery.pkg.apis.meta.v1.ObjectMeta
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def parse_datetime(dt_str: str) -> datetime:
    return datetime.strptime(dt_str, DATETIME_FORMAT).replace(tzinfo=timezone.utc)


def convert_datetime(dt: Union[str, datetime]) -> datetime:
    """
    For use with attrs.
    """
    if isinstance(dt, datetime):
        return dt
    else:
        return parse_datetime(dt)
