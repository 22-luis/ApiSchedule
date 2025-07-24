import enum

class UserState(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class OrderStatus(enum.Enum):
    PENDING = "pending"
    PROGRAMADA = "programada"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"