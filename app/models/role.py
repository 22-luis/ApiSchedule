import enum

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    PLANNER = "planner"
    SUPERVISOR = "supervisor"
    TIMEKEEPER = "timekeeper"
    USER = "user"
    WAREHOUSE = "warehouse"
    ACCOUNTING = "accounting"