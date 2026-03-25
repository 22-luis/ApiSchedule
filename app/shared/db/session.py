from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from app.shared.core.config import settings
from app.shared.utils.core.logging import get_logger

logger = get_logger("database")

# Configurar engine con parámetros optimizados
engine_kwargs = {
    "echo": settings.SQLALCHEMY_ECHO,  # Controlar logs SQL desde configuración
    "pool_pre_ping": settings.DB_POOL_PRE_PING,   # Verificar conexiones antes de usar
    "pool_recycle": settings.DB_POOL_RECYCLE,    # Reciclar conexiones cada hora
    "pool_size": settings.DB_POOL_SIZE,         # Tamaño del pool de conexiones
    "max_overflow": settings.DB_MAX_OVERFLOW,      # Conexiones adicionales permitidas
    "pool_timeout": settings.DB_POOL_TIMEOUT,      # Timeout para obtener conexión
}

# Configuraciones específicas por entorno
if settings.is_production:
    # La configuración de producción ya está en settings
    pass
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
def set_postgresql_timezone(dbapi_connection, connection_record):
    """Configurar la zona horaria en PostgreSQL a America/El_Salvador"""
    if engine.dialect.name == "postgresql":
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("SET TIME ZONE 'America/El_Salvador'")
        except Exception as e:
            logger.warning(f"Could not set timezone: {e}")
        finally:
            cursor.close()

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Configurar pragmas para SQLite (solo en testing)"""
    if settings.ENVIRONMENT == "testing":
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    if settings.DEBUG:
        logger.debug("Conexión obtenida del pool")

@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    if settings.DEBUG:
        logger.debug("Conexión devuelta al pool")


def get_db() -> Session:
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
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        logger.info("Conexión a base de datos exitosa")
        return True
    except Exception as e:
        logger.error(f"Error conectando a la base de datos: {e}")
        return False


def get_database_info() -> dict:
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
