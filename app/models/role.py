"""
Enum que define los diferentes roles de usuario en el sistema.
"""
import enum

class UserRole(enum.Enum):
    ADMIN = "admin"
    PLANNER = "planner"
    SUPERVISOR = "supervisor"
    USER = "user"
    WAREHOUSE = "warehouse"