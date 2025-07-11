import enum

class UserRole(enum.Enum):
    ADMIN = "admin"
    PLANNER = "planner"
    SUPERVISOR = "supervisor"
    USER = "user"