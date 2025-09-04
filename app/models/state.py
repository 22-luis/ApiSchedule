"""
Enums que representan los posibles estados de usuario y de las órdenes en el sistema.
"""
import enum

class UserState(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class OrderStatus(enum.Enum):
    pending = "pending"
    programmed = "programmed"
    unprogrammed = "unprogrammed"
    manufactured = "manufactured"
    completed = "completed"
    
class ProgrammingStatus(enum.Enum):
    available = "available"
    unavailable = "unavailable"
    