import os

import pelorus.utils

_DEFAULT_KEYWORD = (
    os.getenv("PELORUS_DEFAULT_KEYWORD") or pelorus.utils.DEFAULT_VAR_KEYWORD
)
