## API Schedule — Documentación de la API (v1)

Base URL: `/api/v1`

Autenticación: Bearer JWT. Incluye el header en las rutas protegidas:

```
Authorization: Bearer <token>
```

### Roles y estados
- **Roles (`UserRole`)**: `admin`, `planner`, `supervisor`, `user`
- **Estados de usuario (`UserState`)**: `active`, `inactive`
- **Estados de orden (`OrderStatus`)**: `pending`, `programada`, `in_progress`, `completed`

Notas:
- Algunas rutas devuelven objetos serializados manualmente. Los campos tipo enum normalmente se devuelven como string.
- Fechas/horas deben ir en ISO 8601 salvo que se indique lo contrario.

---

### Auth

POST `/api/v1/auth/login`
- **Auth**: pública
- **Body (form-data OAuth2PasswordRequestForm)**:
  - `username`: string
  - `password`: string
- **Respuesta 200**:
  ```json
  {
    "access_token": "<jwt>",
    "token_type": "bearer",
    "user": {
      "id": "<uuid>",
      "username": "<string>",
      "role": "admin|planner|supervisor|user",
      "teamIds": ["<uuid>", "<uuid>"]
    }
  }
  ```

POST `/api/v1/auth/logout`
- **Auth**: requiere token
- **Respuesta 200**: cuerpo vacío

---

### Users

POST `/api/v1/users/`
- **Auth**: pública
- **Body (`UserCreate`)**:
  - `username`: string
  - `password`: string
  - `role`: `admin|planner|supervisor|user`
  - `state`: `active|inactive`
  - `teamIds`: [uuid] (opcional)
- **Respuesta 200 (`UserOut`)**: `id, username, role, state, teamIds`

DELETE `/api/v1/users/{user_id}`
- **Auth**: `admin | planner`
- **Respuesta 200**: `{ "message": "User deleted successfully" }`

PATCH `/api/v1/users/{user_id}`
- **Auth**: `admin | planner`
- **Body (`UserCreate`)**: mismos campos que creación (password reescribe)
- **Respuesta 200 (`UserOut`)**

PATCH `/api/v1/users/{user_id}/state`
- **Auth**: `admin | planner`
- **Body**: `{ "state": "active|inactive" }`
- **Respuesta 200 (`UserOut`)**

GET `/api/v1/users/`
- **Auth**: `admin | planner | supervisor`
- **Query**:
  - `state`: `active|inactive` (opcional)
  - `role`: `admin|planner|supervisor|user` (opcional)
  - `skip`: int (default 0)
  - `limit`: int (1-50, default 10)
  - `search`: string (opcional, por username)
- **Respuesta 200**:
  ```json
  {
    "users": [{"id":"<uuid>","username":"...","role":"...","state":"...","teamIds":["<uuid>"]}],
    "total": 123
  }
  ```

---

### Teams

POST `/api/v1/teams/`
- **Auth**: `admin | planner`
- **Body (`TeamCreate`)**:
  - `name`: string
  - `supervisorId`: uuid (debe ser usuario activo)
  - `userIds`: [uuid] (opcional; solo usuarios activos)
- **Respuesta 200 (`TeamOut`)**: `id, name, supervisorId, supervisorUsername, users`

DELETE `/api/v1/teams/{team_id}`
- **Auth**: `admin | planner`
- **Respuesta 200 (`TeamOut`)**: retorna el equipo eliminado

PATCH `/api/v1/teams/{team_id}`
- **Auth**: `admin | planner`
- **Body (`TeamCreate`)**
- **Respuesta 200 (`TeamOut`)**

GET `/api/v1/teams/`
- **Auth**: requiere token
- Devuelve todos los equipos si el rol es `admin|planner|supervisor`. Si el rol es `user`, devuelve solo los equipos asignados al usuario.
- **Respuesta 200**: lista de `TeamOut`

GET `/api/v1/teams/{team_id}`
- **Auth**: `admin | planner | supervisor`
- Solo incluye usuarios activos en `users`.
- **Respuesta 200 (`TeamOut`)**

---

### Orders

POST `/api/v1/orders/`
- **Auth**: `admin | planner`
- Acepta un objeto `OrderCreate` o una lista de `OrderCreate`.
- **Body (`OrderCreate`)**:
  - `lote`: int
  - `code`: string
  - `status`: `pending|programada|in_progress|completed`
  - `description`: string
  - `quantity`: int
  - `bin`: int
  - `dueDate`: datetime (ISO)
- **Respuesta 200**: lista de órdenes creadas (objetos con los mismos campos de entrada, `status` como string)

DELETE `/api/v1/orders/{order_id}`
- `order_id`: lote (string/int)
- **Auth**: `admin | planner`
- **Respuesta 200**: `{ "message": "Order deleted successfully" }`

PATCH `/api/v1/orders/{order_id}/status`
- **Auth**: `admin | planner`
- **Body**: `{ "status": "pending|programada|in_progress|completed" }`
- **Respuesta 200**: orden actualizada (mismos campos; `status` como string)

GET `/api/v1/orders/`
- **Auth**: `planner | supervisor`
- **Query**:
  - `status`: `pending|programada|in_progress|completed` (opcional)
  - `lote`: int (opcional)
  - `code`: string (opcional)
  - `skip`: int (default 0)
  - `limit`: int (1-100, default 10)
- **Respuesta 200**:
  ```json
  { "orders": [ { "lote": 1, "code": "...", "status": "programada", "description": "...", "quantity": 10, "bin": 1, "dueDate": "2024-01-01T00:00:00" } ], "total": 1 }
  ```

---

### Codes

POST `/api/v1/codes/`
- **Auth**: `admin | planner`
- **Body (`CodeCreate`)**:
  - `code`: string
  - `description`: string
  - `unit`: string
  - `type`: string
  - `activity`: string
  - `quantity`: string (opcional)
  - `time`: number (opcional)
  - `people`: int (opcional)
  - `performance`: number (opcional)
  - `material`: string
  - `presentation`: string
  - `fabricationCode`: string (opcional)
  - `usefulLife`: string
  - `related_code_team`: string (opcional)
  - `teamIds`: [uuid] (opcional)
- **Respuesta 200 (`CodeOut`)**

POST `/api/v1/codes/bulk_upload`
- **Auth**: `admin | planner`
- **Body**: lista de objetos con campos equivalentes a `CodeCreate` (se permiten alias comunes de Excel como `usefullife`, `fabricationc`).
- **Respuesta 200**: `{ "created": <int>, "errors": [ { "row": <n>, "error": "<texto>" } ] }`

GET `/api/v1/codes/`
- **Auth**: `admin | planner | supervisor | user`
- **Query**: `skip` (int, default 0), `limit` (1-100, default 20), `search` (string, opcional; por `code` o `description`)
- **Respuesta 200**: `{ "codes": [CodeOut], "total": <int> }`

GET `/api/v1/codes/by_code_and_activity`
- **Auth**: pública
- **Query**: `code` (string), `activity` (string)
- **Respuesta 200**: objeto Code (campos crudos del modelo)

GET `/api/v1/codes/by_code/{code}/activity`
- **Auth**: pública
- **Respuesta 200**:
  ```json
  { "code": "<code>", "activities": [ { "id": "<uuid>", "activity": "...", "description": "...", ... } ], "total_activities": 3 }
  ```

GET `/api/v1/codes/by_code/{code}/lotes`
- **Auth**: pública
- **Respuesta 200**: `{ "code": "<code>", "lotes": [<int>, <int>] }`

GET `/api/v1/codes/{code_id}`
- **Auth**: `admin | planner | supervisor | user`
- **Respuesta 200 (`CodeOut`)**

PATCH `/api/v1/codes/{code_id}`
- **Auth**: `admin | planner`
- **Body (`CodeUpdate`)**
- **Respuesta 200 (`CodeOut`)**

DELETE `/api/v1/codes/{code_id}`
- **Auth**: `admin | planner`
- **Respuesta 200**: `{ "message": "Code deleted successfully" }`

---

### Preparations

POST `/api/v1/preparations/`
- **Auth**: `admin | planner`
- **Body (`PreparationCreate`)**: `description` (string), `minutes` (int)
- **Respuesta 200 (`PreparationOut`)**

POST `/api/v1/preparations/bulk_upload`
- **Auth**: `admin | planner`
- **Body**: lista de objetos `{ description, minutes }`
- **Respuesta 200**: `{ "created": <int>, "errors": [ { "row": <n>, "error": "<texto>" } ] }`

GET `/api/v1/preparations/`
- **Auth**: `admin | planner | supervisor | user`
- **Respuesta 200**: lista de `PreparationOut`

GET `/api/v1/preparations/{preparation_id}`
- **Auth**: `admin | planner | supervisor`
- **Respuesta 200 (`PreparationOut`)**

PATCH `/api/v1/preparations/{preparation_id}`
- **Auth**: `admin | planner`
- **Body (`PreparationCreate`)**
- **Respuesta 200 (`PreparationOut`)**

DELETE `/api/v1/preparations/{preparation_id}`
- **Auth**: `admin | planner`
- **Respuesta 200**: `{ "message": "Preparation deleted successfully" }`

---

### Tasks

POST `/api/v1/tasks/`
- **Auth**: `admin | planner | supervisor | user`
- Si el rol es `user`, solo puede crear tareas para programaciones de equipos a los que pertenece.
- **Body (`TaskCreate`)**:
  - Requeridos: `total_time` (int), `start_time` (datetime), `end_time` (datetime), `teamIds` ([uuid]), `programming_id` (uuid)
  - Opcionales: `code_id` (uuid), `lote` (string), `quantity` (int), `specification` (string), `preparation_id` (uuid), `minutes` (int), `people` (int), `performance` (number), `material` (string), `presentation` (string), `fabricationCode` (string), `usefulLife` (string), `related_task_code` (string), `unit` (string), `type` (string), `activity` (string), `description` (string)
- **Respuesta 200 (`TaskOut`)**: incluye `code`, `preparation`, `teams`, `created_by_user`

POST `/api/v1/tasks/{task_id}/duplicate`
- **Auth**: `admin | planner | supervisor | user` (con validación de pertenencia si es `user`)
- **Body**: `{ "lote": "<string>" }`
- **Respuesta 200 (`TaskOut`)**

GET `/api/v1/tasks/`
- **Auth**: `admin | planner | supervisor | user`
- **Respuesta 200**: lista de `TaskOut`

GET `/api/v1/tasks/{task_id}`
- **Auth**: `admin | planner | supervisor`
- **Respuesta 200 (`TaskOut`)**

PATCH `/api/v1/tasks/{task_id}`
- **Auth**: `admin | planner | supervisor`
- **Body (`TaskUpdate`)** (todos los campos opcionales)
- **Respuesta 200 (`TaskOut`)**

DELETE `/api/v1/tasks/{task_id}`
- **Auth**: `admin | planner | supervisor`
- **Respuesta 200**: `{ "message": "Task deleted successfully" }`

GET `/api/v1/teams/{team_id}/tasks`
- (ruta anidada)
- **Auth**: `admin | planner | supervisor`
- **Respuesta 200**: lista de `TaskOut`

---

### Programmings

GET `/api/v1/programmings/`
- **Auth**: requiere token; `admin|planner|supervisor` ven todas; `user` ve solo las de sus equipos.
- **Respuesta 200**: lista de `{ id, date, team_id, tasks: [task_id] }`

GET `/api/v1/programmings/by_team_date`
- **Auth**: requiere token
- **Query**: `team_id` (uuid string), `date` (`YYYY-MM-DD`)
- Si no existe y el usuario es `admin|planner|supervisor` o pertenece al equipo, se crea automáticamente.
- **Respuesta 200**: `{ id, date, team_id, tasks: [ TaskOut + campos de programación: start_time, end_time, order, real_start_time, real_end_time, real_quantity, comment, is_completed ] }`

GET `/api/v1/programmings/{programming_id}`
- **Auth**: requiere token y pertenencia o rol elevado
- **Respuesta 200 (`ProgrammingRead`)**

POST `/api/v1/programmings/`
- **Auth**: `admin | planner | supervisor`
- **Body (`ProgrammingCreate`)**: `{ date, team_id, task_ids: [uuid] }`
- **Respuesta 201 (`ProgrammingRead`)**

PUT `/api/v1/programmings/{programming_id}`
- **Auth**: `admin | planner | supervisor`
- **Body (`ProgrammingUpdate`)**
- **Respuesta 200 (`ProgrammingRead`)**

DELETE `/api/v1/programmings/{programming_id}`
- **Auth**: `admin | planner | supervisor`
- **Respuesta 204**: sin contenido

POST `/api/v1/programmings/ensure_by_team_date`
- **Auth**: requiere token
- **Query**: `team_id` (uuid string), `date` (date ISO `YYYY-MM-DD`)
- Crea si no existe; solo `admin|planner|supervisor` pueden crear.
- **Respuesta 200 (`ProgrammingRead`)**

POST `/api/v1/programmings/{programming_id}/add_task`
- **Auth**: requiere token; solo `admin|planner|supervisor`
- **Body**: `{ "task_id": "<uuid>" }`
- **Respuesta 200 (`ProgrammingRead`)**

POST `/api/v1/programmings/{programming_id}/remove_task`
- **Auth**: requiere token; solo `admin|planner|supervisor`
- **Body**: `{ "task_id": "<uuid>" }`
- **Respuesta 200 (`ProgrammingRead`)**

PUT `/api/v1/programmings/{programming_id}/reorder`
- **Auth**: `admin | planner | supervisor`
- **Body**: lista `[ProgrammingTaskOrderIn]` y opcional `base_time` (string `HH:MM`). Si no se envían `start_time/end_time`, se recalculan automáticamente según `base_time` o una hora por defecto.
- **Respuesta 200 (`ProgrammingReorderResponse`)**: `{ programming_id, tasks: [ { task_id, order, start_time, end_time, ... } ] }`

GET `/api/v1/programmings/{programming_id}/last_task`
- **Auth**: requiere token
- **Respuesta 200**: `TaskOut` con campo adicional `programming_end_time`

POST `/api/v1/programmings/{programming_id}/tasks/{task_id}/start_timer`
- **Auth**: requiere token; solo el usuario asignado puede iniciar si ya hubo asignación previa
- **Body (opcional)**: `{ "real_start_time": "<ISO datetime>" }`
- **Respuesta 200**: `{ "ok": true, "real_start_time": "<ISO datetime>" }`

POST `/api/v1/programmings/{programming_id}/tasks/{task_id}/stop_timer`
- **Auth**: requiere token; solo el mismo usuario que inició
- **Body (`ProgrammingTaskReportIn`)**: `{ real_end_time?, real_quantity?, comment? }`
- **Respuesta 200**: `{ "ok": true, "real_end_time": "<ISO>", "real_quantity": <int> }`

POST `/api/v1/programmings/{programming_id}/tasks/{task_id}/comment`
- **Auth**: requiere token; solo el mismo usuario que inició
- **Body (`ProgrammingTaskReportIn`)**: `{ comment }`
- **Respuesta 200**: `{ "ok": true, "comment": "..." }`

POST `/api/v1/programmings/{programming_id}/tasks/{task_id}/toggle_status`
- **Auth**: requiere token
- **Respuesta 200**: `{ "is_completed": true|false }`

---

### Observaciones de integración
- Incluye el header `Authorization` con el token de login para las rutas que lo requieren.
- Campos `date`, `datetime` y `time` deben enviarse en formato ISO.
- En Tasks, `total_time` es requerido por el esquema de entrada aunque la lógica actual no lo utilice.
- En Orders, algunos cambios de estado automáticos pueden ocurrir al iniciar/detener timers de tareas relacionadas a un `lote`.
