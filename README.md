# ApiSchedule

API REST para optimización de programación y asignación de tareas en producción de alimentos. Sistema modular basado en órdenes que gestiona usuarios, roles, equipos y tareas, con funcionalidades de cronometraje y reportes de productividad.

## 🚀 Características Principales

### Gestión de Usuarios y Equipos
- **Sistema de autenticación JWT** con roles jerárquicos (admin, planner, supervisor, user)
- **Membresía de equipos basada en fechas**: Los usuarios pueden pertenecer a múltiples equipos en diferentes períodos
- **Gestión de supervisores** y asignación dinámica de responsabilidades
- **Control de acceso basado en roles** (RBAC)

### Gestión de Órdenes y Programación
- **Control completo de órdenes de producción**: lotes, códigos, estados y trazabilidad
- **Programación inteligente de tareas** con asignación automática a equipos
- **Replicación automática de tareas** (ej: pesado → fabricado → empaque)
- **Cálculos de productividad** centralizados y configurables
- **Sistema de horarios** con soporte para diferentes zonas horarias

### Módulo de Cronometraje (Timer)
- **Cronómetro en tiempo real** para seguimiento de tareas
- **Registro de tiempos** con pausas y reanudaciones
- **Historial de cronometrajes** por usuario y equipo
- **Integración con tareas** para medición de productividad real

### Módulo de Reportes
- **Reportes de productividad** por equipo, usuario y período
- **Análisis de tiempos** reales vs. estimados
- **Métricas de rendimiento** y eficiencia
- **Exportación de datos** para análisis externos

## ✨ Funcionalidades Automáticas

### Tarea de Preparación Automática
- Se crea automáticamente **"REUNION Y PREPARACION DE AREA"** cuando una programación está vacía
- Horario fijo: **07:00 - 07:10** (10 minutos)
- Siempre es la primera tarea en la programación
- Campos limpios: solo información esencial

### Actualización Automática de Estados
- Las órdenes cambian automáticamente de estado según el flujo de trabajo
- **Flujo completo**: Pendiente → Programada → En Progreso → Completada
- Trazabilidad completa del proceso de producción
- Notificaciones de cambios de estado

### Cálculo Inteligente de Tiempos
- Sistema que usa **performance** (horas × cantidad × 60) o tiempo directo
- Cálculo automático basado en la actividad específica
- Manejo de casos edge con valores por defecto
- Ajustes dinámicos según el tipo de tarea

### Selección Automática de Equipos
- Lógica inteligente para asignar el equipo más idóneo según reglas de negocio
- **Reglas específicas por servicio**:
  - Mezcla → Fabricado 1
  - Molino → Molino
  - Pesado → Equipos de pesado disponibles
  - Empaque → Equipos de empaque según actividad
- Optimización automática de recursos y balanceo de carga

### Replicación Automática de Tareas
- **Pesado automático**: Al crear tareas de fabricación, se generan automáticamente tareas de pesado
- **Cadena de producción**: Soporte para flujos de trabajo complejos
- **Configuración flexible**: Reglas de replicación definidas en `app/modules/programming/rules/`

## 🏗️ Arquitectura Modular

El proyecto está organizado en módulos independientes para mejor mantenibilidad:

```
app/
├── modules/
│   ├── core/              # Autenticación, usuarios y equipos
│   │   ├── api/          # Endpoints de auth, users, teams
│   │   ├── models/       # User, Team, UserTeam (membresía)
│   │   ├── schemas/      # Pydantic schemas
│   │   └── services/     # Lógica de negocio
│   │
│   ├── programming/       # Programación y tareas
│   │   ├── api/          # Endpoints de orders, tasks, programming
│   │   ├── models/       # Order, Task, Programming, Preparation
│   │   ├── schemas/      # Schemas de programación
│   │   ├── services/     # Servicios de creación de tareas
│   │   └── rules/        # Reglas de negocio automáticas
│   │       ├── Manufactured.py  # Reglas de fabricación
│   │       ├── weighning.py     # Reglas de pesado
│   │       ├── packaging.py     # Reglas de empaque
│   │       └── schedule.py      # Reglas de programación
│   │
│   ├── timer/             # Cronometraje
│   │   ├── api/          # Endpoints de timer y records
│   │   ├── models/       # Timer, RecordStopwatch
│   │   ├── schemas/      # Schemas de cronometraje
│   │   └── services/     # Lógica de cronómetros
│   │
│   ├── reports/           # Reportes y análisis
│   │   ├── api/          # Endpoints de reportes
│   │   └── services/     # Generación de reportes
│   │
│   └── automation/        # Tareas automatizadas
│       └── services/     # Servicios de automatización
│
├── shared/                # Recursos compartidos
│   ├── core/             # Configuración y seguridad
│   ├── db/               # Configuración de base de datos
│   └── utils/            # Utilidades comunes
│       ├── core/         # Exception handlers, logging, health checks
│       ├── performance/  # Rate limiting, circuit breakers, metrics
│       └── ...           # Otras utilidades
│
└── main.py               # Aplicación FastAPI principal
```

## 🔒 Seguridad y Configuración

- **Configuración basada en Pydantic Settings** con validación automática
- **Rate Limiting inteligente** por IP y usuario
- **Logging estructurado** con diferentes formatos por entorno
- **CORS configurado de forma segura** con orígenes específicos
- **Validación de variables críticas** al inicio de la aplicación
- **Headers de seguridad** y middleware de protección
- **Circuit Breakers** para protección contra fallos en cascada
- **Health Checks** completos para monitoreo

### Configuración por Entorno

- **Desarrollo**: Logging detallado, rate limiting relajado, docs habilitadas
- **Producción**: Logging JSON, rate limiting estricto, SSL requerido, docs deshabilitadas
- **Testing**: Configuración optimizada para tests automatizados

## 📋 Requisitos

- Python 3.8+
- PostgreSQL 12+
- FastAPI 0.104.0+
- SQLAlchemy 2.0.25+
- Alembic 1.13.0+

## 🛠️ Instalación y Configuración

### 1. Clonar el repositorio

```bash
git clone https://github.com/22-luis/ApiSchedule
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
# Seguridad
SECRET_KEY=your-super-secret-key-with-at-least-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Base de datos
POSTGRES_USER=your_postgres_user
POSTGRES_PASSWORD=your_secure_postgres_password
POSTGRES_DB=apischedule_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Aplicación
APP_NAME=ApiSchedule
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60
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
# Desarrollo (con hot-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Producción
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

La aplicación estará disponible en:
- API: http://localhost:8000
- Documentación interactiva: http://localhost:8000/docs
- Documentación alternativa: http://localhost:8000/redoc

## 📡 Endpoints Principales

### Monitoreo
```http
GET /health                    # Health check básico
GET /health/detailed          # Health check detallado
GET /info                     # Información de la aplicación
GET /metrics                  # Métricas de performance (solo dev)
GET /circuit-breakers         # Estado de circuit breakers (solo dev)
GET /rate-limit-stats         # Estadísticas de rate limiting (solo dev)
```

### Autenticación
```http
POST /api/v1/auth/login       # Login con JWT
POST /api/v1/auth/register    # Registro de usuario
GET  /api/v1/auth/me          # Información del usuario actual
```

### Usuarios y Equipos
```http
GET    /api/v1/users          # Listar usuarios
POST   /api/v1/users          # Crear usuario
GET    /api/v1/teams          # Listar equipos
POST   /api/v1/teams          # Crear equipo
PUT    /api/v1/teams/{id}     # Actualizar equipo (con membresías)
```

### Órdenes y Programación
```http
GET    /api/v1/orders         # Listar órdenes
POST   /api/v1/orders         # Crear orden
GET    /api/v1/tasks          # Listar tareas
POST   /api/v1/tasks          # Crear tarea (con auto-replicación)
GET    /api/v1/programming    # Obtener programación
POST   /api/v1/programming    # Crear programación
```

### Timer
```http
GET    /api/v1/timer          # Obtener cronómetros
POST   /api/v1/timer/start    # Iniciar cronómetro
POST   /api/v1/timer/stop     # Detener cronómetro
GET    /api/v1/records        # Historial de cronometrajes
```

### Reportes
```http
GET    /api/v1/reports/productivity    # Reporte de productividad
GET    /api/v1/reports/efficiency      # Reporte de eficiencia
```

## 🔐 Autenticación

La API utiliza autenticación JWT. Para acceder a endpoints protegidos:

```bash
# 1. Login para obtener token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username&password=your_password"

# Respuesta:
# {
#   "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "token_type": "bearer"
# }

# 2. Usar token en requests subsecuentes
curl -X GET "http://localhost:8000/api/v1/users" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 👥 Roles y Permisos

| Rol | Permisos |
|-----|----------|
| **admin** | Acceso completo a todas las funcionalidades, gestión de usuarios y configuración |
| **planner** | Gestión de órdenes, equipos, programación y asignación de tareas |
| **supervisor** | Supervisión de equipos, aprobación de tareas y visualización de reportes |
| **user** | Ejecución de tareas asignadas, uso de cronómetro y visualización de su programación |

## 🧪 Desarrollo y Testing

### Ejecutar tests

```bash
# Instalar dependencias de testing (si no están instaladas)
pip install pytest pytest-asyncio pytest-cov httpx

# Ejecutar todos los tests
pytest

# Ejecutar tests con cobertura
pytest --cov=app --cov-report=html

# Ejecutar tests específicos
pytest app/tests/test_orders.py
pytest app/tests/test_teams.py -v

# Verificación rápida del servidor
python scripts/quick_test.py
```

### Estructura de Tests

```
app/tests/
├── test_auth.py                        # Tests de autenticación
├── test_users.py                       # Tests de gestión de usuarios
├── test_teams.py                       # Tests de equipos y membresías
├── test_orders.py                      # Tests de órdenes
├── test_tasks.py                       # Tests de tareas
├── test_programming.py                 # Tests de programación
├── test_programming_availability.py    # Tests de disponibilidad
├── test_base_task_service.py          # Tests de servicio base
├── test_weighing_task_service.py      # Tests de servicio de pesado
├── test_fabrication_task_service.py   # Tests de servicio de fabricación
├── test_team_selection_service.py     # Tests de selección de equipos
└── test_utils.py                       # Tests de utilidades
```

### Scripts de Utilidad

```
scripts/
├── quick_test.py              # Verificación rápida del servidor
├── find_available_lotes.py    # Búsqueda de lotes disponibles
├── run_tests.py               # Ejecutor de tests personalizado
└── validation_script.py       # Validación de servicios
```

### Generar migraciones

```bash
# Crear nueva migración automática
alembic revision --autogenerate -m "Descripción de los cambios"

# Aplicar migraciones pendientes
alembic upgrade head

# Revertir última migración
alembic downgrade -1

# Ver historial de migraciones
alembic history
```

### Logging

El sistema de logging está configurado automáticamente según el entorno:

- **Desarrollo**: Logs con colores en consola, nivel DEBUG
- **Producción**: Logs JSON en archivo y consola, nivel INFO
- **Niveles**: DEBUG, INFO, WARNING, ERROR, CRITICAL

```python
# Uso en código
from app.shared.utils.core.logging import get_logger

logger = get_logger(__name__)
logger.info("Mensaje informativo")
logger.error("Error ocurrido", exc_info=True)
```

## 🐛 Troubleshooting

### Error: Variables de entorno críticas faltantes

**Síntoma**: La aplicación no inicia y muestra error de configuración.

**Solución**: Verificar que todas las variables críticas estén definidas en `.env`:
```bash
# Variables obligatorias
SECRET_KEY=...
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_DB=...
```

### Error: Conexión a base de datos

**Síntoma**: `sqlalchemy.exc.OperationalError: could not connect to server`

**Solución**:
```bash
# 1. Verificar que PostgreSQL esté ejecutándose
sudo systemctl status postgresql  # Linux
# o
pg_ctl status  # Windows

# 2. Probar conexión manual
psql -h localhost -U your_user -d your_database

# 3. Verificar configuración en .env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

### Error: Rate limiting muy estricto

**Síntoma**: Recibir errores 429 (Too Many Requests) en desarrollo.

**Solución**: Ajustar límites en `.env`:
```bash
RATE_LIMIT_REQUESTS_PER_MINUTE=100
# o deshabilitar temporalmente
RATE_LIMIT_ENABLED=false
```

### Error: Migraciones de Alembic

**Síntoma**: Error al ejecutar `alembic upgrade head`

**Solución**:
```bash
# 1. Verificar estado actual
alembic current

# 2. Ver migraciones pendientes
alembic history

# 3. Si hay conflictos, resolver manualmente o recrear
alembic downgrade base
alembic upgrade head
```

## 📊 Monitoreo y Observabilidad

### Métricas Disponibles

El sistema recopila automáticamente:

- **Requests por minuto** por IP y usuario
- **Tiempo de respuesta** de endpoints (percentiles p50, p95, p99)
- **Errores y excepciones** con contexto completo y stack traces
- **Operaciones de base de datos** con logging de queries lentas
- **Uso de memoria y CPU** del proceso
- **Estado de circuit breakers** para servicios externos

### Health Checks

```bash
# Health check básico (rápido)
curl http://localhost:8000/health

# Health check detallado (incluye DB, memoria, disco)
curl http://localhost:8000/health/detailed
```

### Logs Estructurados

En producción, todos los logs se generan en formato JSON para facilitar el análisis con herramientas como ELK, Splunk o Datadog:

```json
{
  "timestamp": "2024-11-25T15:30:45.123Z",
  "level": "INFO",
  "logger": "app.modules.programming.services.auto_service",
  "message": "Tarea creada automáticamente",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "endpoint": "/api/v1/tasks",
  "status_code": 201,
  "duration": 0.234,
  "user_id": "abc123",
  "task_id": 42,
  "order_id": 88535
}
```

## 🔄 Flujo de Trabajo Típico

### 1. Crear una orden de producción
```bash
POST /api/v1/orders
{
  "lote": "L12345",
  "code_id": 1,
  "quantity": 1000,
  "status": "pendiente"
}
```

### 2. Crear programación para un equipo
```bash
POST /api/v1/programming
{
  "team_id": 1,
  "date": "2024-11-25"
}
```

### 3. Asignar tarea (se crean automáticamente tareas relacionadas)
```bash
POST /api/v1/tasks
{
  "order_id": 1,
  "team_id": 1,
  "programming_id": 1,
  "activity": "Fabricado",
  "start_time": "08:00",
  "end_time": "12:00"
}
# → Se crea automáticamente tarea de "Pesado" si aplica
```

### 4. Iniciar cronómetro para la tarea
```bash
POST /api/v1/timer/start
{
  "task_id": 1,
  "user_id": 1
}
```

### 5. Generar reporte de productividad
```bash
GET /api/v1/reports/productivity?team_id=1&start_date=2024-11-01&end_date=2024-11-30
```

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 👨‍💻 Contribución

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📞 Soporte

Para reportar bugs o solicitar features, por favor abre un issue en GitHub.

---

**Desarrollado con ❤️ usando FastAPI y SQLAlchemy**

