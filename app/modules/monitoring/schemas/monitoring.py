

class AppInfoOut:
    app_name: str
    version: str
    environment: str
    debugging: bool
    database_url: str
    rate_limit: bool

class HealthStatusOut:
    status: str
    timestamp: str
    uptime: float

class DetailsHealthStatusOut:
    pass

class SystemStatusOut:
    pass

