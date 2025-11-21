import enum

class UserState(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
