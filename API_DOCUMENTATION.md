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

### Health Check & Info

GET `/health`
- **Auth**: pública
- **Respuesta 200**:
  ```json
  {
    "status": "healthy",
    "app_name": "ApiSchedule",
    "version": "1.0.0",
    "environment": "development",
    "timestamp": 1234567890.123
  }
  ```

GET `/info`
- **Auth**: pública
- **Respuesta 200**:
  ```json
  {
    "app_name": "ApiSchedule",
    "version": "1.0.0",
    "environment": "development",
    "debug": true,
    "database_configured": true,
    "rate_limiting_enabled": true,
    "cors_origins": ["*"],
    "working_hours": {
      "monday_friday": "7:00 - 17:00",
      "saturday": "7:30 - 17:30",
      "sunday": "No laboral"
    }
  }
  ```

GET `/rate-limit-stats`
- **Auth**: pública (solo en desarrollo)
- **Respuesta 200**: estadísticas de rate limiting

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
- **Respuesta 200 (`UserOut`)`

PATCH `/api/v1/users/{user_id}/state`
- **Auth**: `admin | planner`
- **Body**: `{ "state": "active|inactive" }`
- **Respuesta 200 (`UserOut`)`

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
- **Body (`TeamCreate`)`
- **Respuesta 200 (`TeamOut`)`

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
- **Respuesta 200**: 
  ```json
  {
    "created_orders": [{"lote": 123, "quantity": 100, "code": "PROD-001"}],
    "summary": {"total_orders": 1, "total_quantity": 100, "unique_codes": 1},
    "activities_data": {
      "activities_by_code": {
        "PROD-001": {
          "code": "PROD-001",
          "activities": [
            {
              "id": "uuid1",
              "activity": "FABRICACION",
              "description": "Producto 1 - Fabricación",
              "unit": "pieza",
              "type": "tipo1",
              "quantity": "100",
              "time": 60.0,
              "people": 2,
              "performance": 100.0,
              "material": "material1",
              "presentation": "presentacion1",
              "fabricationCode": "FAB-001",
              "usefulLife": "12"
            }
          ],
          "total_activities": 1,
          "found": true
        }
      },
      "total_codes_processed": 1,
      "codes_processed": ["PROD-001"]
    },
    "message": "Se crearon 1 órdenes exitosamente con sus actividades"
  }
  ```

DELETE `/api/v1/orders/{order_id}`
- `order_id`: lote (string/int)
- **Auth**: `admin | planner`
- **Respuesta 200**: `{ "message": "Order deleted successfully" }`

PATCH `/api/v1/orders/{order_id}/status`
- **Auth**: `admin | planner`
- **Body**: `{ "status": "pending|programada|in_progress|completed" }`
- **Respuesta 200**: orden actualizada (mismos campos; `status` como string)

POST `/api/v1/orders/{order_id}/sync_status`
- **Auth**: `admin | planner`
- Sincroniza el estado de una orden basándose en el estado actual de todas sus tareas.
- **Respuesta 200**: orden actualizada con estado sincronizado

POST `/api/v1/orders/{order_id}/sync_status_simple`
- **Auth**: `admin | planner`
- Sincroniza el estado de una orden sin validación de esquema (para debug).
- **Respuesta 200**:
  ```json
  {
    "success": true,
    "order_id": "123",
    "status_before": "pending",
    "status_after": "in_progress",
    "changed": true,
    "order": { ... }
  }
  ```

POST `/api/v1/orders/sync_all_status`
- **Auth**: `admin | planner`
- Sincroniza el estado de todas las órdenes basándose en el estado actual de sus tareas.
- **Respuesta 200**:
  ```json
  {
    "message": "Synced 50 out of 100 orders",
    "synced_count": 50,
    "total_orders": 100
  }
  ```

POST `/api/v1/orders/update_status_for_today`
- **Auth**: `admin | planner`
- Actualiza automáticamente el estado de las órdenes que tienen tareas programadas para hoy.
- **Respuesta 200**:
  ```json
  {
    "message": "Updated 10 orders for today's programming",
    "updated_count": 10,
    "total_today_tasks": 15
  }
  ```

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

GET `/api/v1/orders/test-sync/{order_id}`
- **Auth**: `admin | planner`
- Endpoint de prueba para sincronizar el estado de una orden.
- **Respuesta 200**:
  ```json
  {
    "success": true,
    "order_id": "123",
    "status_before": "pending",
    "status_after": "in_progress",
    "changed": true,
    "order": { ... }
  }
  ```

POST `/api/v1/orders/extract-data`
- **Auth**: `admin | planner`
- Extrae datos de órdenes específicas por sus lotes.
- **Body**: `{"order_ids": [12345, 12346, 12347]}`
- **Respuesta 200**:
  ```json
  {
    "extracted_orders": [{"lote": 12345, "code": "PROD-001", "status": "pending", "description": "Producto 1", "quantity": 100, "bin": 1, "dueDate": "2024-01-15T00:00:00", "created_at": null, "metadata": {"is_new": true, "extraction_timestamp": "now"}}],
    "processing_data": [{"lote": 12345, "code": "PROD-001", "status": "pending", "description": "Producto 1", "quantity": 100, "bin": 1, "dueDate": "2024-01-15T00:00:00", "processing_info": {"can_be_programmed": true, "requires_attention": false, "is_completed": false}}],
    "summary": {"total_orders": 1, "status_summary": {"pending": 1}, "total_quantity": 100, "unique_codes": 1, "codes": ["PROD-001"]},
    "requested_lotes": [12345, 12346, 12347],
    "found_lotes": [12345],
    "missing_lotes": [12346, 12347]
  }
  ```

GET `/api/v1/orders/extract-recent`
- **Auth**: `admin | planner`
- Extrae datos de las órdenes más recientes.
- **Query**:
  - `limit`: int (1-100, default 10)
  - `status`: `pending|programada|in_progress|completed` (opcional)
- **Respuesta 200**:
  ```json
  {
    "extracted_orders": [{"lote": 12350, "quantity": 50, "code": "PROD-005"}],
    "summary": {"total_orders": 1, "total_quantity": 50, "unique_codes": 1},
    "limit": 5,
    "status_filter": "pending",
    "message": "Se extrajeron 1 órdenes recientes"
  }
  ```

POST `/api/v1/orders/extract-with-activities`
- **Auth**: `admin | planner`
- Extrae datos de órdenes específicas y obtiene las actividades para cada código.
- **Body**: `{"order_ids": [12345, 12346, 12347]}`
- **Respuesta 200**:
  ```json
  {
    "extracted_orders": [{"lote": 12345, "quantity": 100, "code": "PROD-001"}],
    "summary": {"total_orders": 1, "total_quantity": 100, "unique_codes": 1},
    "activities_data": {
      "activities_by_code": {
        "PROD-001": {
          "code": "PROD-001",
          "activities": [
            {
              "id": "uuid1",
              "activity": "FABRICACION",
              "description": "Producto 1 - Fabricación",
              "unit": "pieza",
              "type": "tipo1",
              "quantity": "100",
              "time": 60.0,
              "people": 2,
              "performance": 100.0,
              "material": "material1",
              "presentation": "presentacion1",
              "fabricationCode": "FAB-001",
              "usefulLife": "12"
            }
          ],
          "total_activities": 1,
          "found": true
        }
      },
      "total_codes_processed": 1,
      "codes_processed": ["PROD-001"]
    },
    "requested_lotes": [12345, 12346, 12347],
    "found_lotes": [12345],
    "missing_lotes": [12346, 12347]
  }
  ```

GET `/api/v1/orders/extract-recent-with-activities`
- **Auth**: `admin | planner`
- Extrae datos de las órdenes más recientes y obtiene las actividades para cada código.
- **Query**:
  - `limit`: int (1-100, default 10)
  - `status`: `pending|programada|in_progress|completed` (opcional)
- **Respuesta 200**:
  ```json
  {
    "extracted_orders": [{"lote": 12350, "quantity": 50, "code": "PROD-005"}],
    "summary": {"total_orders": 1, "total_quantity": 50, "unique_codes": 1},
    "activities_data": {
      "activities_by_code": {
        "PROD-005": {
          "code": "PROD-005",
          "activities": [
            {
              "id": "uuid3",
              "activity": "FABRICACION",
              "description": "Producto 5 - Fabricación",
              "unit": "kg",
              "type": "tipo2",
              "quantity": "50",
              "time": 45.0,
              "people": 3,
              "performance": 95.0,
              "material": "material3",
              "presentation": "presentacion3",
              "fabricationCode": "FAB-005",
              "usefulLife": "6"
            }
          ],
          "total_activities": 1,
          "found": true
        }
      },
      "total_codes_processed": 1,
      "codes_processed": ["PROD-005"]
    },
    "limit": 5,
    "status_filter": "pending",
    "message": "Se extrajeron 1 órdenes recientes con sus actividades"
  }
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
- **Respuesta 200 (`CodeOut`)`

PATCH `/api/v1/codes/{code_id}`
- **Auth**: `admin | planner`
- **Body (`CodeUpdate`)`
- **Respuesta 200 (`CodeOut`)`

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
- **Respuesta 200 (`PreparationOut`)`

PATCH `/api/v1/preparations/{preparation_id}`
- **Auth**: `admin | planner`
- **Body (`PreparationCreate`)`
- **Respuesta 200 (`PreparationOut`)`

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
- **Respuesta 200 (`TaskOut`)`

GET `/api/v1/tasks/`
- **Auth**: `admin | planner | supervisor | user`
- **Respuesta 200**: lista de `TaskOut`

GET `/api/v1/tasks/{task_id}`
- **Auth**: `admin | planner | supervisor`
- **Respuesta 200 (`TaskOut`)`

PATCH `/api/v1/tasks/{task_id}`
- **Auth**: `admin | planner | supervisor`
- **Body (`TaskUpdate`)** (todos los campos opcionales)
- **Respuesta 200 (`TaskOut`)`

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
- **Respuesta 200 (`ProgrammingRead`)`

POST `/api/v1/programmings/`
- **Auth**: `admin | planner | supervisor`
- **Body (`ProgrammingCreate`)**: `{ date, team_id, task_ids: [uuid] }`
- **Respuesta 201 (`ProgrammingRead`)`

PUT `/api/v1/programmings/{programming_id}`
- **Auth**: `admin | planner | supervisor`
- **Body (`ProgrammingUpdate`)`
- **Respuesta 200 (`ProgrammingRead`)`

DELETE `/api/v1/programmings/{programming_id}`
- **Auth**: `admin | planner | supervisor`
- **Respuesta 204**: sin contenido

POST `/api/v1/programmings/ensure_by_team_date`
- **Auth**: requiere token
- **Query**: `team_id` (uuid string), `date` (date ISO `YYYY-MM-DD`)
- Crea si no existe; solo `admin|planner|supervisor` pueden crear.
- **Respuesta 200 (`ProgrammingRead`)`

POST `/api/v1/programmings/{programming_id}/add_task`
- **Auth**: requiere token; solo `admin|planner|supervisor`
- **Body**: `{ "task_id": "<uuid>" }`
- **Respuesta 200 (`ProgrammingRead`)`

POST `/api/v1/programmings/{programming_id}/remove_task`
- **Auth**: requiere token; solo `admin|planner|supervisor`
- **Body**: `{ "task_id": "<uuid>" }`
- **Respuesta 200 (`ProgrammingRead`)`

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

POST `/api/v1/programmings/{programming_id}/tasks/{task_id}/reprogram`
- **Auth**: requiere token
- **Body**: `{ "new_date": "<YYYY-MM-DD>" }`
- Reprograma una tarea para una nueva fecha y actualiza el estado de la orden correspondiente.
- **Respuesta 200**: `{ "message": "Task reprogrammed successfully" }`

---

### Calculations

POST `/api/v1/calculations/task-duration`
- **Auth**: requiere token
- **Body (`TaskDurationRequest`)**:
  - `quantity`: int
  - `productivity`: float
  - `people`: int
- **Respuesta 200 (`TaskDurationResponse`)**:
  ```json
  {
    "minutes": 150,
    "hours": 2.5,
    "formula": "minutos = (cantidad × productividad × 60) ÷ personas"
  }
  ```

GET `/api/v1/calculations/task-duration/simple`
- **Auth**: requiere token
- **Query**:
  - `quantity`: int
  - `productivity`: float
  - `people`: int
- **Respuesta 200**: `{ "minutes": 150 }`

POST `/api/v1/calculations/working-hours`
- **Auth**: requiere token
- **Body (`WorkingHoursRequest`)**:
  - `date`: date (YYYY-MM-DD)
- **Respuesta 200 (`WorkingHoursResponse`)**:
  ```json
  {
    "start_time": "07:00",
    "end_time": "17:00",
    "is_working_day": true,
    "total_hours": 10
  }
  ```

GET `/api/v1/calculations/working-hours/{target_date}`
- **Auth**: requiere token
- **Respuesta 200**: mismo formato que POST `/working-hours`

GET `/api/v1/calculations/programming-base-time/{target_date}`
- **Auth**: requiere token
- **Respuesta 200**:
  ```json
  {
    "base_time": "07:00:00",
    "is_working_day": true
  }
  ```

POST `/api/v1/calculations/sequential-times`
- **Auth**: `admin | planner | supervisor`
- **Body (`SequentialTimesRequest`)**:
  - `base_date`: date
  - `base_time`: string (opcional, HH:MM)
  - `tasks`: lista de objetos con campo `minutes`
- **Respuesta 200**:
  ```json
  {
    "base_date": "2024-01-01",
    "base_time": "07:00",
    "tasks": [
      {
        "start_time": "07:00",
        "end_time": "09:30",
        "minutes": 150
      }
    ]
  }
  ```

POST `/api/v1/calculations/validate-task-parameters`
- **Auth**: requiere token
- **Query**:
  - `quantity`: int
  - `productivity`: float
  - `people`: int
- **Respuesta 200**:
  ```json
  {
    "is_valid": true,
    "errors": []
  }
  ```

GET `/api/v1/calculations/formula-info`
- **Auth**: requiere token
- **Respuesta 200**: información sobre las fórmulas de cálculo utilizadas

POST `/api/v1/calculations/validate-task-form`
- **Auth**: requiere token
- **Body**: `{ "form_data": { ... } }`
- Valida los datos completos de un formulario de tarea.
- **Respuesta 200**: resultado de validación

POST `/api/v1/calculations/validate-extra-task`
- **Auth**: requiere token
- **Body**:
  - `description`: string
  - `minutes`: string
  - `selected_team`: string
  - `programming_id`: string
- **Respuesta 200**: resultado de validación

POST `/api/v1/calculations/task-efficiency`
- **Auth**: requiere token
- **Body**:
  - `planned_minutes`: int
  - `actual_minutes`: int
- **Respuesta 200**: cálculo de eficiencia

POST `/api/v1/calculations/team-workload`
- **Auth**: requiere token
- **Body**:
  - `tasks`: lista de tareas
  - `working_hours`: int (default 8)
- **Respuesta 200**: cálculo de carga de trabajo del equipo

POST `/api/v1/calculations/format-time-el-salvador`
- **Auth**: requiere token
- **Body**: `{ "time_str": "<ISO time>" }`
- **Respuesta 200**:
  ```json
  {
    "formatted_time": "7:00 AM",
    "original_time": "07:00:00"
  }
  ```

GET `/api/v1/calculations/programming-base-time-utc/{target_date}`
- **Auth**: requiere token
- **Respuesta 200**:
  ```json
  {
    "base_time_utc": "2024-01-01T13:00:00Z",
    "is_working_day": true,
    "el_salvador_time": "7:00 AM"
  }
  ```

GET `/api/v1/calculations/timezone-info`
- **Auth**: requiere token
- **Respuesta 200**: información sobre el manejo de zonas horarias

---

### Observaciones de integración
- Incluye el header `Authorization` con el token de login para las rutas que lo requieren.
- Campos `date`, `datetime` y `time` deben enviarse en formato ISO.
- En Tasks, `total_time` es requerido por el esquema de entrada aunque la lógica actual no lo utilice.
- En Orders, algunos cambios de estado automáticos pueden ocurrir al iniciar/detener timers de tareas relacionadas a un `lote`.
- Los endpoints de cálculos centralizan funciones que anteriormente estaban en el frontend.
- El sistema maneja automáticamente la replicación de tareas en equipos de tipo 'pesado' cuando se asignan tareas a equipos 'fabricado' o 'molino' con ciertas actividades.

## Endpoints de Programación

### Obtener Programaciones Disponibles por Equipo

**Endpoint:** `GET /programmings/team/{team_uuid}/available`

**Descripción:** Obtiene las programaciones con estado 'available' para un equipo específico, desde la fecha actual hacia adelante. Si no existen programaciones futuras, crea automáticamente una programación para el día siguiente a la última programación existente.

**Parámetros:**
- `team_uuid` (UUID, requerido): ID del equipo para el cual buscar programaciones disponibles

**Permisos requeridos:**
- Usuarios con rol `admin`, `planner`, o `supervisor` pueden acceder a cualquier equipo
- Usuarios regulares solo pueden acceder a equipos a los que pertenecen

**Respuesta exitosa (200):**
```json
{
  "team_id": "uuid-del-equipo",
  "team_name": "Nombre del Equipo",
  "available_programmings": [
    {
      "id": "uuid-de-la-programacion",
      "team_name": "Nombre del Equipo",
      "date": "2024-01-15"
    }
  ]
}
```

**Respuestas de error:**
- `404 Not Found`: El equipo no existe
- `403 Forbidden`: El usuario no tiene permisos para acceder al equipo

**Ejemplo de uso:**
```bash
curl -X GET "http://localhost:8000/programmings/team/123e4567-e89b-12d3-a456-426614174000/available" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Comportamiento especial:**
- Si no existen programaciones futuras disponibles, el sistema automáticamente crea una nueva programación para el día siguiente a la última programación existente del equipo
- Si el equipo no tiene ninguna programación, se crea una programación para mañana
- Solo se devuelven programaciones con estado 'available' (disponible)
- Las fechas se devuelven en formato ISO (YYYY-MM-DD)

---

### Obtener Solo Programaciones Disponibles Existentes

**Endpoint:** `GET /programmings/team/{team_uuid}/available-only`

**Descripción:** Obtiene SOLO las programaciones existentes con estado 'available' para un equipo específico, desde la fecha actual hacia adelante. NO crea nuevas programaciones automáticamente.

**Parámetros:**
- `team_uuid` (UUID, requerido): ID del equipo para el cual buscar programaciones disponibles

**Permisos requeridos:**
- Usuarios con rol `admin`, `planner`, o `supervisor` pueden acceder a cualquier equipo
- Usuarios regulares solo pueden acceder a equipos a los que pertenecen

**Respuesta exitosa (200):**
```json
{
  "team_id": "uuid-del-equipo",
  "team_name": "Nombre del Equipo",
  "available_programmings": [
    {
      "id": "uuid-de-la-programacion",
      "team_name": "Nombre del Equipo",
      "date": "2024-01-15"
    }
  ]
}
```

**Ejemplo de uso:**
```bash
curl -X GET "http://localhost:8000/programmings/team/123e4567-e89b-12d3-a456-426614174000/available-only" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### Crear Nueva Programación Disponible

**Endpoint:** `POST /programmings/team/{team_uuid}/create-next-available`

**Descripción:** Crea una nueva programación disponible para el día siguiente a la última programación existente del equipo. Solo para administradores, planners y supervisores.

**Parámetros:**
- `team_uuid` (UUID, requerido): ID del equipo para el cual crear la programación

**Permisos requeridos:**
- Solo usuarios con rol `admin`, `planner`, o `supervisor`

**Respuesta exitosa (200):**
```json
{
  "id": "uuid-de-la-nueva-programacion",
  "team_name": "Nombre del Equipo",
  "date": "2024-01-16"
}
```

**Respuestas de error:**
- `404 Not Found`: El equipo no existe
- `403 Forbidden`: El usuario no tiene permisos para crear programaciones
- `400 Bad Request`: Ya existe una programación para la fecha calculada

**Ejemplo de uso:**
```bash
curl -X POST "http://localhost:8000/programmings/team/123e4567-e89b-12d3-a456-426614174000/create-next-available" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Comportamiento:**
- Busca la última programación del equipo
- Calcula la fecha para la nueva programación (día siguiente a la última)
- Si no hay programaciones previas, crea una para mañana
- Verifica que no exista ya una programación para esa fecha
- Crea la nueva programación con estado 'available'

---

## Nuevos Endpoints de Equipos de Pesado

### Obtener Equipo Más Idóneo para Pesado

**Endpoint:** `GET /api/v1/orders/weighing/most-suitable-team`

**Descripción:** Obtiene el equipo más idóneo para actividades de pesado.

**Permisos requeridos:**
- Usuarios con rol `admin`, `planner`, `supervisor`, o `user`

**Respuesta exitosa (200):**
```json
{
  "success": true,
  "message": "Equipo más idóneo para pesado encontrado: Pesado Principal",
  "weighing_teams": [
    {
      "id": "team1",
      "name": "Pesado Principal",
      "is_most_suitable": true
    },
    {
      "id": "team2",
      "name": "Pesado 1",
      "is_most_suitable": false
    }
  ],
  "most_suitable_team": {
    "id": "team1",
    "name": "Pesado Principal",
    "supervisor_id": "supervisor1"
  },
  "total_weighing_teams": 2
}
```

**Respuestas de error:**
- `500 Internal Server Error`: Error al obtener equipos de pesado

**Ejemplo de uso:**
```bash
curl -X GET "http://localhost:8000/api/v1/orders/weighing/most-suitable-team" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Obtener Equipo Más Idóneo para Pesado (Endpoint de Equipos)

**Endpoint:** `GET /api/v1/teams/weighing/most-suitable`

**Descripción:** Obtiene el equipo más idóneo para actividades de pesado desde el endpoint de equipos.

**Permisos requeridos:**
- Usuarios con rol `admin`, `planner`, `supervisor`, o `user`

**Respuesta:** Misma estructura que el endpoint anterior

**Ejemplo de uso:**
```bash
curl -X GET "http://localhost:8000/api/v1/teams/weighing/most-suitable" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Lógica de selección:**
1. Busca equipos que contengan "pesado" en el nombre
2. Prioridad: "pesado principal" > "pesado 1" > primer equipo con "pesado"
3. Incluye ID, nombre y supervisor del equipo seleccionado

---

## Nuevos Endpoints de Equipos de Pesado con Programaciones

### Obtener Equipo Más Idóneo para Pesado con Programaciones

**Endpoint:** `GET /api/v1/orders/weighing/most-suitable-team-with-programmings`

**Descripción:** Obtiene el equipo más idóneo para pesado junto con sus programaciones disponibles desde la fecha actual. Si no hay programaciones disponibles, crea automáticamente una nueva programación.

**Permisos requeridos:**
- Usuarios con rol `admin`, `planner`, `supervisor`, o `user`

**Respuesta exitosa (200):**
```json
{
  "success": true,
  "message": "Equipo más idóneo para pesado y programaciones obtenidos exitosamente",
  "team_data": {
    "success": true,
    "message": "Equipo más idóneo para pesado encontrado exitosamente",
    "total_weighing_teams": 3,
    "most_suitable_team": {
      "id": 2,
      "name": "pesado principal",
      "supervisor_id": 5
    }
  },
  "available_programmings": {
    "success": true,
    "message": "Programaciones disponibles obtenidas exitosamente",
    "team_id": 2,
    "team_name": "pesado principal",
    "current_date": "2024-01-15",
    "total_available_programmings": 1,
    "programmings": [
      {
        "id": 10,
        "date": "2024-01-16",
        "status": "available",
        "total_tasks": 0,
        "is_newly_created": true
      }
    ]
  }
}
```

**Respuestas de error:**
- `500 Internal Server Error`: Error al obtener equipo o programaciones

**Ejemplo de uso:**
```bash
curl -X GET "http://localhost:8000/api/v1/orders/weighing/most-suitable-team-with-programmings" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Lógica:**
1. Obtiene el equipo más idóneo para pesado
2. Busca programaciones disponibles para ese equipo desde la fecha actual
3. Si no hay programaciones disponibles:
   - Obtiene la última programación del equipo
   - Calcula la fecha para la nueva programación (un día después de la última)
   - Evita domingos (pasa al lunes)
   - Verifica que no exista ya una programación para esa fecha
   - Crea una nueva programación con estado "available"
4. Filtra por estado "available" y ordena por fecha

---

## Nuevos Endpoints de Verificación de Límite de Tiempo

### Verificar Límite de Tiempo para Programación

**Endpoint:** `POST /api/v1/orders/weighing/verify-time-limit`

**Descripción:** Verifica que al agregar una tarea a una programación no se exceda el límite de tiempo (17:40) más de 5 minutos. Si la programación está vacía, crea automáticamente una tarea de preparación.

**Permisos requeridos:**
- Usuarios con rol `admin`, `planner`, `supervisor`, o `user`

**Request Body:**
```json
{
  "programmings": [
    {
      "id": "prog1",
      "date": "2024-01-15",
      "status": "available",
      "team_id": "team1"
    }
  ],
  "task_minutes": 60
}
```

**Respuesta exitosa (200):**
```json
{
  "success": true,
  "message": "Programación seleccionada que cumple con límite de tiempo",
  "selected_programming": {
    "id": "prog1",
    "date": "2024-01-15",
    "team_id": "team1",
    "team_name": "Pesado Principal",
    "current_end_time": "16:20:00",
    "task_minutes": 60,
    "final_time": "17:20:00",
    "time_limit": "17:40:00",
    "tolerance_minutes": 5
  },
  "verification_details": {
    "current_end_minutes": 980,
    "final_minutes": 1040,
    "max_allowed_minutes": 1065,
    "within_limit": true
  }
}
```

**Nota:** Si la programación seleccionada estaba vacía, se crea automáticamente una tarea de preparación con:
- Descripción: "REUNION Y PREPARACION DE AREA"
- Horario: 7:00 - 7:10
- Minutos: 10
- Estado: "completed"

**Respuestas de error:**
- `400 Bad Request`: Datos de entrada inválidos
- `500 Internal Server Error`: Error al verificar límite de tiempo

**Ejemplo de uso:**
```bash
curl -X POST "http://localhost:8000/api/v1/orders/weighing/verify-time-limit" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "programmings": [
      {
        "id": "prog1",
        "date": "2024-01-15",
        "status": "available",
        "team_id": "team1"
      }
    ],
    "task_minutes": 60
  }'
```

**Lógica de funcionamiento:**
1. Define límite de tiempo: 17:40 + 5 minutos de tolerancia (17:45 máximo)
2. Para cada programación en la lista:
   - Obtiene la última tarea y su end_time
   - Calcula el tiempo final si se agrega la nueva tarea
   - Verifica si no excede el límite de 17:45
   - Si cumple, retorna esa programación
3. Si ninguna programación cumple, retorna error

### Obtener Equipo con Verificación de Tiempo

**Endpoint:** `POST /api/v1/orders/weighing/team-with-time-verification`

**Descripción:** Obtiene el equipo más idóneo para pesado, sus programaciones disponibles y verifica el límite de tiempo.

**Permisos requeridos:**
- Usuarios con rol `admin`, `planner`, `supervisor`, o `user`

**Request Body:**
```json
{
  "task_minutes": 45
}
```

**Respuesta exitosa (200):**
```json
{
  "success": true,
  "message": "Equipo idóneo, programaciones y verificación de tiempo obtenidos exitosamente",
  "team_data": {
    "success": true,
    "message": "Equipo más idóneo para pesado encontrado exitosamente",
    "total_weighing_teams": 3,
    "most_suitable_team": {
      "id": 2,
      "name": "pesado principal",
      "supervisor_id": 5
    }
  },
  "available_programmings": {
    "success": true,
    "message": "Programaciones disponibles obtenidas exitosamente",
    "team_id": 2,
    "team_name": "pesado principal",
    "current_date": "2024-01-15",
    "total_available_programmings": 3,
    "programmings": [...]
  },
  "time_verification": {
    "success": true,
    "message": "Programación seleccionada que cumple con límite de tiempo",
    "selected_programming": {
      "id": "prog1",
      "date": "2024-01-15",
      "team_name": "Pesado Principal",
      "final_time": "17:05:00"
    }
  }
}
```

**Respuestas de error:**
- `400 Bad Request`: Datos de entrada inválidos
- `500 Internal Server Error`: Error al obtener equipo o verificar tiempo

**Ejemplo de uso:**
```bash
curl -X POST "http://localhost:8000/api/v1/orders/weighing/team-with-time-verification" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_minutes": 45
  }'
```

**Lógica de funcionamiento:**
1. Obtiene el equipo más idóneo para pesado
2. Busca programaciones disponibles para ese equipo
3. Verifica límite de tiempo para cada programación
4. Retorna la primera programación que cumple con el límite de tiempo
