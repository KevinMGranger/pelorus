import logging


class FORMATS:
    time = "%(asctime)-15s"
    level = "%(levelname)-8s"

    prelude = f"{time} {level}"

    msg = "%(message)s"

    debug_location = "%(pathname)s:%(lineno)d %(funcName)s()"

    debug_prelude = f"{prelude} {debug_location}"


DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "%(asctime)-15s %(levelname)-8s %(message)s"
DEFAULT_LOG_DATE_FORMAT = "%m-%d-%Y %H:%M:%S"

DEBUG_FORMAT = (
    "%(asctime)-15s %(levelname)-8s %(pathname)s:%(lineno)d %(funcName)s() %(message)s"
)

# class SpecializeDebugFormatter(logging.Formatter):
#     """
#     Uses a different format for DEBUG messages that has more information.
#     """

#     DEBUG_FORMAT = "%(asctime)-15s %(levelname)-8s %(pathname)s:%(lineno)d %(funcName)s() %(message)s"

#     def format(self, record):
#         prior_format = self._style._fmt

#         try:
#             if record.levelno == logging.DEBUG:
#                 self._style._fmt = self.DEBUG_FORMAT

#             return logging.Formatter.format(self, record)
#         finally:
#             self._style._fmt = prior_format


def non_debug_only(record: logging.LogRecord):
    return record.levelname != "DEBUG"


def debug_only(record: logging.LogRecord):
    return record.levelname == "DEBUG"
