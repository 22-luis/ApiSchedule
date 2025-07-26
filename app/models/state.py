"""
Enums que representan los posibles estados de usuario y de las órdenes en el sistema.
"""
import enum

class UserState(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class OrderStatus(enum.Enum):
    pending = "pending"
    programada = "programada"
    in_progress = "in_progress"
    completed = "completed"