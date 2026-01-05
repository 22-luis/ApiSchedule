# Documentación Backend - Proyecto Frontend Programaciones

Este documento detalla **únicamente** los endpoints y flujos del backend que son consumidos actualmente por el proyecto `frontend/programacionesHermel`.

## 🔐 Autenticación y Sesión
Manejado principalmente por el hook `useAuth`.

| Método | Endpoint | Descripción | Uso en Frontend |
|--------|----------|-------------|-----------------|
| `POST` | `/auth/login` | Iniciar sesión | `useAuth.ts`: Envía `username` y `password` (form-data). Recibe JWT. |
| `POST` | `/auth/logout` | Cerrar sesión | `useAuth.ts`: Invalida la sesión actual en el backend. |

---

## 📅 Programación y Dashboard
Endpoints para visualizar y gestionar la carga de trabajo diaria.

| Método | Endpoint | Descripción | Uso en Frontend |
|--------|----------|-------------|-----------------|
| `GET` | `/programmings/` | Obtener programaciones | `api.ts`: `getProgrammingsByDate(date)`. Obtiene la matriz de programación para todos los equipos en una fecha. |
| `GET` | `/programmings/{id}/last_task` | Última tarea programada | `useTaskForm.ts`: Se usa para calcular la hora de inicio sugerida de una nueva tarea (continuidad). |

---

## 📦 Órdenes y Estado
Gestión de órdenes de producción y sincronización de estados.

| Método | Endpoint | Descripción | Uso en Frontend |
|--------|----------|-------------|-----------------|
| `GET` | `/orders` | Buscar/Listar órdenes | `api.ts`: `getPackagedOrders(...)` y `orderStatusService.ts`. Filtra por `lote`, `code`, `status`. |
| `POST` | `/orders/sync-status` | Forzar sincronización | `orderStatusService.ts`: `syncAllOrders` y `syncSpecificOrders`. Recalcula estados de órdenes basado en tareas. |
| `POST` | `/orders/{id}/deliver` | Entregar orden | `api.ts`: `deliverOrder`. Cambia el estado a entregado y registra cantidad. |

---

## 📝 Tareas (Operaciones y Cronómetro)
Endpoints utilizados en el formulario de tareas y control de tiempos.

| Método | Endpoint | Descripción | Uso en Frontend |
|--------|----------|-------------|-----------------|
| `POST` | `/tasks/` | Crear tarea | `useTaskForm.ts`: Crea tareas manuales o "extra". |
| `PATCH` | `/tasks/{id}` | Actualizar tarea | `useTaskForm.ts`: Edición de tareas existentes. |
| `GET` | `/tasks/{id}` | Detalle de tarea | `orderStatusService.ts`: Obtiene info para procesar cambios de estado. |
| `POST` | `/stopwatch/status` | Estado de cronómetros | `api.ts`: `getTaskStatuses`. Verifica si tareas específicas tienen timer activo. |
| `GET` | `/record-stopwatch/{id}` | Historial tiempos | `api.ts`: `getRecordStopwatchInfo`. Obtiene detalles de tiempos registrados. |

---

## 🏷️ Códigos y Catálogos
Búsqueda de productos y validación de actividades.

| Método | Endpoint | Descripción | Uso en Frontend |
|--------|----------|-------------|-----------------|
| `GET` | `/codes/` | Listar códigos | `api.ts`: `getCodes`. Paginación de códigos generales. |
| `GET` | `/codes/by_code/{c}/activity` | Actividades por código | `useTaskForm.ts`: Valida código y obtiene actividades permitidas (ej. Empaque, Pesado). |
| `GET` | `/codes/by_code/{c}/lotes` | Lotes activos por código | `useTaskForm.ts`: Autocompletado de lotes disponibles para el código seleccionado. |
| `GET` | `/preparations/` | Listar preparaciones | `useTaskForm.ts`: Carga catálogo de preparaciones iniciales. |

---

## � Equipos
Información de equipos de trabajo.

| Método | Endpoint | Descripción | Uso en Frontend |
|--------|----------|-------------|-----------------|
| `GET` | `/teams/{id}` | Detalle equipo | `api.ts`: Obtiene nombre y miembros de un equipo. |
| `GET` | `/teams/by-ids` | Múltiples equipos | `api.ts`: Carga información masiva de equipos para listas. |

---

## ⚙️ Reglas de Negocio Frontend Importantes

1. **Cálculo de Tiempos Local vs Backend**:
   - El frontend intenta usar cálculos del backend (`businessCalculations`), pero tiene "fallbacks" locales si falla la red.
   - **Nota**: `api.ts` define un interceptor que maneja automáticamente tokens `Bearer` desde `localStorage`.

2. **Sincronización de Estados (`orderStatusService`)**:
   - El frontend dispara `/orders/sync-status` periódicamente o tras editar tareas para asegurar que la orden "padre" refleje el progreso real.

3. **Zona Horaria**:
   - `useTaskForm.ts` realiza conversiones manuales a `America/El_Salvador` (UTC-6) para mostrar horas amigables al usuario.
