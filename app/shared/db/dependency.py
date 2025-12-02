"""
Dependencias de base de datos para la aplicación.
Re-exporta las funciones principales para mantener compatibilidad.
"""
from app.shared.db.session import get_db, test_database_connection, get_database_info

# Re-exportar para mantener compatibilidad con código existente
__all__ = ["get_db", "test_database_connection", "get_database_info"]