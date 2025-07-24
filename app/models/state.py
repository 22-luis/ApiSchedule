import enum

class UserState(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class OrderStatus(enum.Enum):
    pending = "pending"
    programada = "programada"
    in_progress = "in_progress"
    completed = "completed"