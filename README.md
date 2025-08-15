# ApiSchedule

API para optimización de programación y asignación de tareas en producción de alimentos. Sistema basado en órdenes que gestiona usuarios, roles y equipos, asignando tareas a responsabilidades específicas para una operación eficiente.

## 🚀 Características Principales

- **Gestión de Usuarios y Roles**: Sistema de autenticación con roles jerárquicos (admin, planner, supervisor, user)
- **Gestión de Equipos**: Asignación de usuarios a equipos con supervisores
- **Gestión de Órdenes**: Control de lotes, códigos y estados de producción
- **Programación de Tareas**: Asignación inteligente de tareas a equipos
- **Cálculos de Negocio**: Centralización de fórmulas y cálculos de productividad
- **Sistema de Horarios**: Gestión de horarios de trabajo y zonas horarias

## 🛡️ Seguridad y Configuración

### ✅ Mejoras de Seguridad Implementadas

- **Configuración basada en Pydantic Settings** con validación automática
- **Rate Limiting inteligente** por IP y usuario
- **Logging estructurado** con diferentes formatos por entorno
- **CORS configurado de forma segura** con orígenes específicos
- **Validación de variables críticas** al inicio de la aplicación
- **Headers de seguridad** y middleware de protección

### 🔧 Configuración por Entorno

- **Desarrollo**: Logging detallado, rate limiting relajado
- **Producción**: Logging JSON, rate limiting estricto, SSL requerido
- **Testing**: Configuración optimizada para tests

## 📋 Requisitos

- Python 3.8+
- PostgreSQL 12+
- FastAPI 0.104.0+
- SQLAlchemy 2.0.23+

## 🚀 Instalación y Configuración

### 1. Clonar el repositorio

```bash
git clone <repository-url>
cd ApiSchedule
```

### 2. Crear entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
# Copiar archivo de ejemplo
cp env.example .env

# Editar variables críticas
nano .env
```

**Variables críticas requeridas:**
```bash
SECRET_KEY=your-super-secret-key-with-at-least-32-characters
POSTGRES_USER=your_postgres_user
POSTGRES_PASSWORD=your_secure_postgres_password
POSTGRES_DB=apischedule_db
```

### 5. Configurar base de datos

```bash
# Crear base de datos PostgreSQL
createdb apischedule_db

# Ejecutar migraciones
alembic upgrade head
```

### 6. Ejecutar la aplicación

```bash
# Desarrollo
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Producción
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📊 Endpoints de Monitoreo

### Health Check
```http
GET /health
```

### Información de la Aplicación
```http
GET /info
```

### Estadísticas de Rate Limiting (solo desarrollo)
```http
GET /rate-limit-stats
```

## 🔐 Autenticación

La API utiliza autenticación JWT. Para acceder a endpoints protegidos:

```bash
# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username&password=your_password"

# Usar token en requests
curl -X GET "http://localhost:8000/api/v1/users" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 📚 Documentación

- **API Documentation**: `/docs` (Swagger UI)
- **ReDoc Documentation**: `/redoc`
- **Configuration Guide**: [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)
- **API Reference**: [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

## 🏗️ Estructura del Proyecto

```
ApiSchedule/
├── app/
│   ├── api/v1/           # Endpoints de la API
│   ├── core/             # Configuración central
│   ├── db/               # Configuración de base de datos
│   ├── models/           # Modelos SQLAlchemy
│   ├── schemas/          # Esquemas Pydantic
│   └── utils/            # Utilidades y helpers
├── alembic/              # Migraciones de base de datos
├── logs/                 # Archivos de log (generados)
├── env.example           # Variables de entorno de ejemplo
├── requirements.txt      # Dependencias Python
└── README.md            # Este archivo
```

## 🔒 Roles y Permisos

- **admin**: Acceso completo a todas las funcionalidades
- **planner**: Gestión de órdenes, equipos y programación
- **supervisor**: Supervisión de equipos y tareas
- **user**: Ejecución de tareas asignadas

## 🛠️ Desarrollo

### Ejecutar tests

```bash
# Instalar dependencias de testing
pip install pytest pytest-asyncio httpx

# Ejecutar tests
pytest
```

### Generar migraciones

```bash
# Crear nueva migración
alembic revision --autogenerate -m "Description of changes"

# Aplicar migraciones
alembic upgrade head
```

### Logging

El sistema de logging está configurado automáticamente:

- **Desarrollo**: Logs con colores en consola
- **Producción**: Logs JSON en archivo y consola
- **Niveles**: DEBUG, INFO, WARNING, ERROR, CRITICAL

## 🚨 Troubleshooting

### Error: Variables de entorno críticas faltantes

Verificar que todas las variables críticas estén definidas en `.env`:
- `SECRET_KEY`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`

### Error: Conexión a base de datos

```bash
# Verificar que PostgreSQL esté ejecutándose
sudo systemctl status postgresql

# Probar conexión
psql -h localhost -U your_user -d your_database
```

### Error: Rate limiting muy estricto

En desarrollo, puedes ajustar los límites:
```bash
RATE_LIMIT_REQUESTS_PER_MINUTE=100
# o deshabilitar temporalmente
RATE_LIMIT_ENABLED=false
```

## 📈 Monitoreo y Observabilidad

### Métricas Disponibles

- **Requests por minuto** por IP y usuario
- **Tiempo de respuesta** de endpoints
- **Errores y excepciones** con contexto completo
- **Operaciones de base de datos** con logging

### Logs Estructurados

En producción, todos los logs se generan en formato JSON para facilitar el análisis:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "logger": "app.main",
  "message": "Request completada",
  "request_id": "uuid-here",
  "method": "GET",
  "endpoint": "/api/v1/users",
  "status_code": 200,
  "duration": 0.123,
  "user_id": "user-hash"
}
```

## 🤝 Contribución

1. Fork el proyecto
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 📞 Soporte

Para soporte técnico o preguntas:
- Crear un issue en GitHub
- Revisar la documentación en `/docs`
- Consultar la guía de configuración

---

**ApiSchedule** - Optimizando la programación de producción de alimentos 🚀
