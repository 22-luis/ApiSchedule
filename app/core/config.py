"""
Configuración centralizada de la aplicación usando Pydantic Settings.
Proporciona validación de tipos, valores por defecto seguros y gestión de variables de entorno.
"""
import os
from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración principal de la aplicación"""
    
    # Configuración de la aplicación
    APP_NAME: str = "ApiSchedule"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, description="Modo debug")
    ENVIRONMENT: str = Field(default="development", description="Entorno de ejecución")
    
    # Configuración de seguridad
    SECRET_KEY: str = Field(default="default-secret-key-change-in-production", description="Clave secreta para JWT")
    ALGORITHM: str = Field(default="HS256", description="Algoritmo para JWT")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=1, le=1440, description="Expiración del token en minutos")
    
    # Configuración de base de datos
    POSTGRES_USER: str = Field(default="postgres", description="Usuario de PostgreSQL")
    POSTGRES_PASSWORD: str = Field(default="password", description="Contraseña de PostgreSQL")
    POSTGRES_DB: str = Field(default="apischedule_db", description="Nombre de la base de datos")
    POSTGRES_SERVER: str = Field(default="localhost", description="Servidor PostgreSQL")
    POSTGRES_PORT: str = Field(default="5432", description="Puerto PostgreSQL")
    POSTGRES_SSL_MODE: str = Field(default="prefer", description="Modo SSL para PostgreSQL")
    
    # Configuración de CORS - usar string por defecto para evitar problemas de parsing
    CORS_ORIGINS_STR: str = Field(default="*", description="Orígenes CORS como string")
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="Permitir credenciales en CORS")
    CORS_ALLOW_METHODS_STR: str = Field(default="GET,POST,PUT,DELETE,PATCH,OPTIONS", description="Métodos HTTP como string")
    CORS_ALLOW_HEADERS_STR: str = Field(default="*", description="Headers como string")
    
    # Configuración de logging
    LOG_LEVEL: str = Field(default="INFO", description="Nivel de logging")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Formato de logging"
    )
    SQLALCHEMY_ECHO: bool = Field(default=False, description="Mostrar queries SQL en logs")
    SQLALCHEMY_LOG_LEVEL: str = Field(default="WARNING", description="Nivel de logging para SQLAlchemy")
    
    # Configuración de rate limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Habilitar rate limiting")
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=1200, ge=1, description="Requests por minuto")
    
    # Configuración de zona horaria
    DEFAULT_TIMEZONE: str = Field(default="America/El_Salvador", description="Zona horaria por defecto")
    
    # Configuración de horarios de trabajo
    WORKING_HOURS_MONDAY_FRIDAY: str = Field(default="07:00-21:00", description="Horario L-V")
    WORKING_HOURS_SATURDAY: str = Field(default="07:30-12:30", description="Horario Sábado")
    WORKING_HOURS_SUNDAY: str = Field(default="00:00-00:00", description="Horario Domingo (no laboral)")
    
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
    
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Convierte el string de CORS_ORIGINS en lista"""
        return [origin.strip() for origin in self.CORS_ORIGINS_STR.split(",")]
    
    @property
    def CORS_ALLOW_METHODS(self) -> List[str]:
        """Convierte el string de CORS_ALLOW_METHODS en lista"""
        return [method.strip().upper() for method in self.CORS_ALLOW_METHODS_STR.split(",")]
    
    @property
    def CORS_ALLOW_HEADERS(self) -> List[str]:
        """Convierte el string de CORS_ALLOW_HEADERS en lista"""
        return [header.strip() for header in self.CORS_ALLOW_HEADERS_STR.split(",")]
    
    @validator("SECRET_KEY")
    def validate_secret_key(cls, v):
        """Valida que la clave secreta tenga la longitud mínima"""
        if len(v) < 32:
            print("⚠️  ADVERTENCIA: SECRET_KEY debe tener al menos 32 caracteres")
            print("   La aplicación puede no funcionar correctamente en producción")
        return v
    
    @validator("POSTGRES_PASSWORD")
    def validate_postgres_password(cls, v):
        """Valida que la contraseña de PostgreSQL no esté vacía"""
        if not v or v == "password":
            print("⚠️  ADVERTENCIA: POSTGRES_PASSWORD no puede estar vacía o ser 'password'")
            print("   La aplicación puede no funcionar correctamente")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        # Permitir campos extra para evitar errores con variables de entorno no definidas
        extra = "ignore"


# Instancia global de configuración
settings = Settings()

# Configuración específica por entorno
class DevelopmentSettings(Settings):
    """Configuración para desarrollo"""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    CORS_ORIGINS_STR: str = "http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000"
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 600  # 10 requests por segundo en desarrollo
    SQLALCHEMY_ECHO: bool = False  # Desactivar logs SQL en desarrollo por defecto
    SQLALCHEMY_LOG_LEVEL: str = "WARNING"  # Solo warnings y errores de SQLAlchemy


class ProductionSettings(Settings):
    """Configuración para producción"""
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"
    POSTGRES_SSL_MODE: str = "require"
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 30
    SQLALCHEMY_ECHO: bool = False  # Nunca mostrar queries SQL en producción
    SQLALCHEMY_LOG_LEVEL: str = "ERROR"  # Solo errores críticos de SQLAlchemy


class TestingSettings(Settings):
    """Configuración para testing"""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    POSTGRES_DB: str = "test_database"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 5


def get_settings() -> Settings:
    """Obtiene la configuración según el entorno"""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        return ProductionSettings()
    elif environment == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()


# Función para validar configuración crítica
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
        print(f"⚠️  Variables de entorno críticas faltantes: {', '.join(missing_vars)}")
        print("   La aplicación puede no funcionar correctamente.")
        return False
    
    return True
