import enum

class UserState(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class OrderStatus(enum.Enum):
    pending = "pending"
    programmed = "programmed"
    unprogrammed = "unprogrammed"
    manufactured = "manufactured"
    delivered = "delivered"
    completed = "completed"
    not_programmable = "not_programmable"
    
class ProgrammingStatus(enum.Enum):
    available = "available"
    unavailable = "unavailable"
    