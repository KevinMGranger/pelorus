import logging
from contextvars import ContextVar
from typing import Optional

import pelorus._logging

namespace: ContextVar[Optional[str]] = ContextVar("namespace", default=None)
app: ContextVar[Optional[str]] = ContextVar("app", default=None)
build: ContextVar[Optional[str]] = ContextVar("build", default=None)


class Formatter(logging.Formatter):
    def __init__(self):
        # TODO: date format?
        super().__init__()

    def formatMessage(self, record: logging.LogRecord):
        if record.levelname == "DEBUG":
            format = pelorus._logging.FORMATS.debug_prelude
        else:
            format = pelorus._logging.FORMATS.prelude

        for attr in [namespace, app, build]:
            value = getattr(self.ctx, attr, None)
            if value is not None:
                format += f" {attr}=%({attr})s"
                setattr(record, attr, value)

        format += " %(message)s"

        return format % record.__dict__


# logger = logging.getLogger()

# fmt = logging.Formatter(
#     "%(asctime)-15s %(levelname)-8s namespace=%(namespace)s app=%(app)s build=%(build_name)s %(message)s"
# )

# handler = logging.StreamHandler()
# handler.setFormatter(fmt)
# handler.addFilter(CommittimeLogFilter())
# logger.addHandler(handler)

# logger.setLevel("DEBUG")
