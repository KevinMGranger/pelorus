# override's attrs.NOTHING's type in a way that's nicer for type checking.
import enum

class _NothingType(enum.Enum):
    NOTHING = enum.auto()

NOTHING = _NothingType.NOTHING
