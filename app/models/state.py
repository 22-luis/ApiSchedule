import enum

class UserState(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class OrderStatus(str, enum.Enum):
    pending = "pending"
    programmed = "programmed"
    unprogrammed = "unprogrammed"
    manufactured = "manufactured"
    delivered = "delivered"
    completed = "completed"
    not_programmable = "not_programmable"
    
class ProgrammingStatus(str, enum.Enum):
    available = "available"
    unavailable = "unavailable"

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"

class TimerStatus(str, enum.Enum):
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"