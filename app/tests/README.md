# Tests para ApiSchedule

Este directorio contiene todos los tests para la API de ApiSchedule. Los tests están organizados por módulos y cubren funcionalidades específicas de la aplicación.

## Estructura de Tests

```
app/tests/
├── __init__.py
├── conftest.py              # Configuración y fixtures de pytest
├── test_auth.py            # Tests de autenticación
├── test_users.py           # Tests de gestión de usuarios
├── test_teams.py           # Tests de gestión de equipos
├── test_tasks.py           # Tests de gestión de tareas
├── test_programming.py     # Tests de gestión de programaciones
├── test_orders.py          # Tests de gestión de órdenes
├── test_utils.py           # Tests de utilidades y lógica de negocio
└── README.md               # Este archivo
```

## Configuración

### Dependencias

Los tests requieren las siguientes dependencias (ya incluidas en `requirements.txt`):

- `pytest>=7.4.0`
- `pytest-asyncio>=0.21.0`
- `pytest-cov>=4.1.0`
- `httpx>=0.25.0`

### Base de Datos de Pruebas

Los tests utilizan una base de datos SQLite en memoria para evitar interferencias con la base de datos de desarrollo/producción. La configuración se encuentra en `conftest.py`.

## Ejecutar Tests

### Ejecutar todos los tests

```bash
# Desde el directorio raíz del proyecto
pytest

# Con más detalles
pytest -v

# Con cobertura de código
pytest --cov=app --cov-report=html
```

### Ejecutar tests específicos

```bash
# Tests de autenticación
pytest app/tests/test_auth.py

# Tests de usuarios
pytest app/tests/test_users.py

# Tests de equipos
pytest app/tests/test_teams.py

# Tests de tareas
pytest app/tests/test_tasks.py

# Tests de programaciones
pytest app/tests/test_programming.py

# Tests de órdenes
pytest app/tests/test_orders.py

# Tests de utilidades
pytest app/tests/test_utils.py
```

### Ejecutar tests por marcadores

```bash
# Solo tests de autenticación
pytest -m auth

# Solo tests de usuarios
pytest -m users

# Solo tests de equipos
pytest -m teams

# Solo tests de tareas
pytest -m tasks

# Solo tests de programaciones
pytest -m programming

# Solo tests de órdenes
pytest -m orders

# Solo tests de utilidades
pytest -m utils

# Excluir tests lentos
pytest -m "not slow"
```

### Opciones adicionales

```bash
# Ejecutar tests en paralelo (requiere pytest-xdist)
pytest -n auto

# Generar reporte de cobertura en HTML
pytest --cov=app --cov-report=html

# Ejecutar tests con detección de cambios automática
pytest-watch

# Ejecutar tests con timeout
pytest --timeout=30
```

## Cobertura de Tests

Los tests cubren las siguientes áreas:

### 1. Autenticación (`test_auth.py`)
- ✅ Login de usuarios
- ✅ Registro de usuarios
- ✅ Validación de tokens
- ✅ Refresh de tokens
- ✅ Logout
- ✅ Manejo de credenciales inválidas

### 2. Gestión de Usuarios (`test_users.py`)
- ✅ CRUD completo de usuarios
- ✅ Gestión de roles y permisos
- ✅ Asociación de usuarios con equipos
- ✅ Validación de permisos por rol
- ✅ Manejo de errores de autorización

### 3. Gestión de Equipos (`test_teams.py`)
- ✅ CRUD completo de equipos
- ✅ Asociación de usuarios con equipos
- ✅ Asociación de tareas con equipos
- ✅ Asociación de códigos con equipos
- ✅ Gestión de supervisores

### 4. Gestión de Tareas (`test_tasks.py`)
- ✅ CRUD completo de tareas
- ✅ Asociación de tareas con programaciones
- ✅ Duplicación de tareas
- ✅ Validación de datos de tareas
- ✅ Gestión de equipos asignados

### 5. Gestión de Programaciones (`test_programming.py`)
- ✅ CRUD completo de programaciones
- ✅ Ordenamiento de tareas
- ✅ Control de tiempo (start/stop)
- ✅ Reportes de ejecución
- ✅ Filtros por fecha y equipo

### 6. Gestión de Órdenes (`test_orders.py`)
- ✅ CRUD completo de órdenes
- ✅ Gestión de estados de órdenes
- ✅ Filtros por estado, fecha, código
- ✅ Órdenes vencidas
- ✅ Resúmenes y estadísticas

### 7. Utilidades y Lógica de Negocio (`test_utils.py`)
- ✅ Health checks
- ✅ Información de la aplicación
- ✅ Cálculos de eficiencia
- ✅ Cálculos de productividad
- ✅ Cálculos de capacidad
- ✅ Validación y limpieza de datos
- ✅ Manejo de excepciones
- ✅ Middleware (CORS, logging, rate limiting)

## Fixtures Disponibles

### Usuarios
- `test_user`: Usuario regular
- `test_admin`: Usuario administrador
- `test_supervisor`: Usuario supervisor
- `test_planner`: Usuario planificador

### Autenticación
- `auth_headers`: Headers de autenticación para usuario regular
- `admin_auth_headers`: Headers de autenticación para administrador
- `supervisor_auth_headers`: Headers de autenticación para supervisor
- `planner_auth_headers`: Headers de autenticación para planificador

### Entidades
- `test_team`: Equipo de prueba
- `test_task`: Tarea de prueba
- `test_programming`: Programación de prueba
- `test_order`: Orden de prueba
- `test_code`: Código de prueba
- `test_preparation`: Preparación de prueba

### Utilidades
- `client`: Cliente de prueba de FastAPI
- `db`: Sesión de base de datos de prueba

## Mejores Prácticas

### 1. Organización de Tests
- Cada archivo de test corresponde a un módulo específico
- Los tests están organizados en clases por funcionalidad
- Cada test tiene un nombre descriptivo y documentación

### 2. Fixtures
- Usar fixtures para datos de prueba reutilizables
- Limpiar datos después de cada test
- Usar scope apropiado para fixtures (function, class, session)

### 3. Aserciones
- Usar aserciones específicas y descriptivas
- Verificar tanto casos exitosos como casos de error
- Validar estructura de respuestas JSON

### 4. Manejo de Errores
- Probar casos de error comunes (401, 403, 404, 422)
- Verificar mensajes de error apropiados
- Probar validaciones de datos

### 5. Base de Datos
- Usar transacciones para aislar tests
- Limpiar datos después de cada test
- No depender del estado de otros tests

## Troubleshooting

### Problemas Comunes

1. **Error de importación de módulos**
   ```bash
   # Asegúrate de estar en el directorio raíz del proyecto
   cd /path/to/ApiSchedule
   pytest
   ```

2. **Error de base de datos**
   ```bash
   # Verifica que las dependencias estén instaladas
   pip install -r requirements.txt
   ```

3. **Tests fallando por permisos**
   ```bash
   # Verifica que los fixtures de autenticación estén correctos
   # Revisa los tokens JWT en conftest.py
   ```

4. **Problemas de cobertura**
   ```bash
   # Regenera la cobertura
   pytest --cov=app --cov-report=html --cov-report=term-missing
   ```

### Debugging

Para debuggear tests específicos:

```bash
# Ejecutar un test específico con más información
pytest app/tests/test_auth.py::TestAuth::test_login_success -v -s

# Ejecutar tests con pdb
pytest --pdb

# Ejecutar tests con detención en fallos
pytest -x
```

## Contribución

Al agregar nuevos tests:

1. Sigue la convención de nombres existente
2. Agrega documentación para nuevos tests
3. Usa fixtures existentes cuando sea posible
4. Agrega marcadores apropiados
5. Verifica la cobertura de código
6. Ejecuta todos los tests antes de hacer commit

## Reportes

Los tests generan varios tipos de reportes:

- **Cobertura de código**: `htmlcov/index.html`
- **Reporte XML**: `coverage.xml`
- **Reporte de terminal**: Muestra tests pasando/fallando
- **Reporte de errores**: Detalles de tests fallidos
