import enum

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    PLANNER = "planner"
    SUPERVISOR = "supervisor"
    TIMEKEEPER = "timekeeper"
    USER = "user"
    WAREHOUSE = "warehouse"
    ACCOUNTING = "accounting"
    QC_COORDINATOR = "qc_coordinator"
    QC_ASSISTANT = "qc_assistant"