import time

from prometheus_client import start_http_server
from prometheus_client.core import REGISTRY

import deploytime.collector_github
import deploytime.collector_openshift
import pelorus
import pelorus.utils

if __name__ == "__main__":
    provider = pelorus.utils.get_env_var("PROVIDER", "").lower() or "openshift"

    if provider == "openshift":
        collector = deploytime.collector_openshift.make_collector()
    elif provider == "github":
        collector = deploytime.collector_github.make_collector()
    else:
        raise ValueError(f"Unknown provider {provider}")

    REGISTRY.register(collector)
    start_http_server(8080)
    while True:
        time.sleep(1)
