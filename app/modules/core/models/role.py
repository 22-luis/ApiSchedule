import enum

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    PLANNER = "planner"
    SUPERVISOR = "supervisor"
    TIMEKEEPER = "timekeeper"
    USER = "user"
    WAREHOUSE = "warehouse"
    ACCOUNTING = "accounting"
    QC_ENGINEER = "qc_engineer"
    QC_TECHNICIAN = "qc_technician"