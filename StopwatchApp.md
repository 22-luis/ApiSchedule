# Documentación Backend - Proyecto Frontend Stopwatch

Este documento detalla **únicamente** los endpoints y flujos del backend que son consumidos actualmente por el proyecto `frontend/Stopwatch`.

## Autenticación
Gestionado por `useAuth.ts`.

| Método | Endpoint | Descripción | Uso en Frontend |
|--------|----------|-------------|-----------------|
| `POST` | `/api/v1/auth/login` | Iniciar sesión | `useAuth.ts`: Autenticación de usuario. Recibe credenciales, devuelve token. |
| `POST` | `/api/v1/auth/logout` | Cerrar sesión | `useAuth.ts`: Cierra la sesión activa. |

---

## Cronómetro y Tiempos (Record Stopwatch)
Funcionalidades centrales de la aplicación de cronómetro.

| Método | Endpoint | Descripción | Uso en Frontend |
|--------|----------|-------------|-----------------|
| `POST` | `/api/v1/stopwatch/status/timer` | Estado de tareas | `api.ts`: `getTaskStatuses`. Verifica estado de temporizadores activos. |
| `GET` | `/api/v1/record-stopwatch/{id}` | Info de registro | `api.ts`: `getRecordStopwatchInfo`. Obtiene detalles de un registro de tiempo específico. |
| `POST` | `/api/v1/record-stopwatch/{id}/comment` | Comentarios | `api.ts`: `addCommentToRecord`. Añade notas a un registro de tiempo. |

---

## Códigos y Catálogos
Validación y autocompletado en formularios.

| Método | Endpoint | Descripción | Uso en Frontend |
|--------|----------|-------------|-----------------|
| `GET` | `/codes/by_code/{c}/activity` | Actividades | `useTaskForm.ts`: Valida código y lista actividades asociadas. |
| `GET` | `/codes/by_code/{c}/lotes` | Lotes | `useTaskForm.ts`: Lista lotes disponibles para un código. |
| `GET` | `/api/v1/preparations/` | Preparaciones | `useTaskForm.ts`: Carga catálogo de preparaciones. |

---

## Notas Importantes

1. **Prefijo de API**:
   - A diferencia de otros proyectos, este frontend llama explícitamente a `/api/v1/...` en la mayoría de sus rutas definidas en `api.ts` y hooks.

2. **Cálculos de Negocio**:
   - Utiliza `businessCalculations` (librería compartida/copiada) para validaciones complejas antes de enviar datos al backend.

3. **Manejo de Errores**:
   - `api.ts` tiene un interceptor que redirige al login si recibe un `401 Unauthorized` y emite un evento `session-expired`.
