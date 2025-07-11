import enum

class UserState(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class OrderState(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"