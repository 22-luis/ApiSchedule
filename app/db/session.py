"""
Configuración de sesión de base de datos usando SQLAlchemy.
Proporciona conexión segura y configuración optimizada.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger("database")

# Configurar engine con parámetros optimizados
engine_kwargs = {
    "echo": settings.SQLALCHEMY_ECHO,  # Controlar logs SQL desde configuración
    "pool_pre_ping": True,   # Verificar conexiones antes de usar
    "pool_recycle": 3600,    # Reciclar conexiones cada hora
    "pool_size": 10,         # Tamaño del pool de conexiones
    "max_overflow": 20,      # Conexiones adicionales permitidas
}

# Configuraciones específicas por entorno
if settings.is_production:
    engine_kwargs.update({
        "pool_size": 20,
        "max_overflow": 30,
        "pool_recycle": 1800,  # Reciclar cada 30 minutos en producción
    })
elif settings.ENVIRONMENT == "testing":
    engine_kwargs.update({
        "poolclass": StaticPool,  # Pool estático para testing
        "connect_args": {"check_same_thread": False}
    })

# Crear engine
try:
    engine = create_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        **engine_kwargs
    )
    logger.info("Engine de base de datos creado correctamente")
except Exception as e:
    logger.error(f"Error creando engine de base de datos: {e}")
    raise

# Configurar session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Eventos para logging de conexiones
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Configurar pragmas para SQLite (solo en testing)"""
    if settings.ENVIRONMENT == "testing":
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log cuando se obtiene una conexión del pool"""
    if settings.DEBUG:
        logger.debug("Conexión obtenida del pool")

@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log cuando se devuelve una conexión al pool"""
    if settings.DEBUG:
        logger.debug("Conexión devuelta al pool")


def get_db() -> Session:
    """
    Dependency para obtener sesión de base de datos.
    Maneja automáticamente el cierre de la sesión.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Error en sesión de base de datos: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def test_database_connection() -> bool:
    """
    Prueba la conexión a la base de datos.
    
    Returns:
        bool: True si la conexión es exitosa, False en caso contrario
    """
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        logger.info("Conexión a base de datos exitosa")
        return True
    except Exception as e:
        logger.error(f"Error conectando a la base de datos: {e}")
        return False


def get_database_info() -> dict:
    """
    Obtiene información sobre la configuración de la base de datos.
    
    Returns:
        dict: Información de configuración de la base de datos
    """
    return {
        "database_url": settings.SQLALCHEMY_DATABASE_URI.replace(
            settings.POSTGRES_PASSWORD, "***"
        ),
        "pool_size": engine_kwargs.get("pool_size"),
        "max_overflow": engine_kwargs.get("max_overflow"),
        "pool_recycle": engine_kwargs.get("pool_recycle"),
        "echo": engine_kwargs.get("echo"),
        "ssl_mode": settings.POSTGRES_SSL_MODE,
        "connection_test": test_database_connection()
    }
