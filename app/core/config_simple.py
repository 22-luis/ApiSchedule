"""
Configuración simple temporal para permitir que la aplicación inicie.
Esta versión no depende de pydantic-settings.
"""
import os
from typing import List
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class Settings:
    """Configuración principal de la aplicación"""
    
    # Configuración de la aplicación
    APP_NAME: str = "ApiSchedule"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Configuración de seguridad
    SECRET_KEY: str = os.getenv("SECRET_KEY", "default-secret-key-change-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Configuración de base de datos
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "password")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "apischedule_db")
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_SSL_MODE: str = os.getenv("POSTGRES_SSL_MODE", "prefer")
    
    # Configuración de CORS
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
    CORS_ALLOW_CREDENTIALS: bool = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
    CORS_ALLOW_METHODS: List[str] = os.getenv("CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE,PATCH,OPTIONS").split(",")
    CORS_ALLOW_HEADERS: List[str] = os.getenv("CORS_ALLOW_HEADERS", "*").split(",")
    
    # Configuración de logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # Configuración de rate limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))
    
    # Configuración de zona horaria
    DEFAULT_TIMEZONE: str = os.getenv("DEFAULT_TIMEZONE", "America/El_Salvador")
    
    # Configuración de horarios de trabajo
    WORKING_HOURS_MONDAY_FRIDAY: str = os.getenv("WORKING_HOURS_MONDAY_FRIDAY", "07:00-17:00")
    WORKING_HOURS_SATURDAY: str = os.getenv("WORKING_HOURS_SATURDAY", "07:30-17:30")
    WORKING_HOURS_SUNDAY: str = os.getenv("WORKING_HOURS_SUNDAY", "00:00-00:00")
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Construye la URI de conexión a la base de datos"""
        ssl_mode = f"?sslmode={self.POSTGRES_SSL_MODE}" if self.POSTGRES_SSL_MODE != "disable" else ""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}{ssl_mode}"
        )
    
    @property
    def is_production(self) -> bool:
        """Verifica si está en producción"""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Verifica si está en desarrollo"""
        return self.ENVIRONMENT.lower() == "development"


# Instancia global de configuración
settings = Settings()


def validate_critical_settings():
    """Valida que las configuraciones críticas estén presentes"""
    critical_vars = [
        "SECRET_KEY",
        "POSTGRES_USER", 
        "POSTGRES_PASSWORD",
        "POSTGRES_DB"
    ]
    
    missing_vars = []
    for var in critical_vars:
        if not getattr(settings, var, None):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  Advertencia: Variables de entorno críticas faltantes: {', '.join(missing_vars)}")
        print("   La aplicación puede no funcionar correctamente.")
        return False
    
    return True
