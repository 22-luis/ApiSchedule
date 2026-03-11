import enum

class ProgrammingStatus(str, enum.Enum):
    available = "available"
    unavailable = "unavailable"

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"