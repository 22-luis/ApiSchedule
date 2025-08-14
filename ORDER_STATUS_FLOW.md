# Flujo de Estados de Órdenes - Documentación

## Resumen

Se ha implementado un sistema centralizado para manejar automáticamente los cambios de estado de las órdenes basándose en las acciones realizadas en las tareas. El flujo sigue la siguiente secuencia:

**pendiente → programada → en progreso → completada**

## Arquitectura

### Servicio Centralizado

El sistema utiliza `OrderStatusService` (`app/utils/order_status_service.py`) que centraliza toda la lógica de cambio de estados, evitando la duplicación de código en diferentes partes de la aplicación.

### Estados de Orden

```python
class OrderStatus(enum.Enum):
    pending = "pending"        # Estado inicial
    programada = "programada"  # Tarea creada
    in_progress = "in_progress" # Tarea en ejecución
    completed = "completed"    # Tarea completada
```

## Flujo Detallado

### 1. Creación de Orden
- **Estado inicial**: `pending`
- **Trigger**: Se crea una nueva orden
- **Lógica**: Estado por defecto

### 2. Creación de Tarea
- **Cambio**: `pending` → `programada`
- **Trigger**: Se crea una tarea con un lote que corresponde a una orden
- **Lógica**: `OrderStatusService.update_order_status_for_task_creation()`
- **Condiciones**:
  - La orden debe existir
  - El estado actual debe ser `pending`
  - El lote de la tarea debe coincidir con el lote de la orden

### 3. Inicio de Tarea
- **Cambio**: `pending` o `programada` → `in_progress`
- **Trigger**: Se inicia una tarea (se establece `real_start_time`)
- **Lógica**: `OrderStatusService.update_order_status_for_task_start()`
- **Condiciones**:
  - La tarea debe ejecutarse hoy
  - El estado actual debe ser `pending` o `programada`

### 3b. Cambio Automático por Fecha de Programación
- **Cambio**: `pending` o `programada` → `in_progress`
- **Trigger**: La fecha de programación coincide con el día actual
- **Lógica**: `OrderStatusService.update_order_status_for_programming_date()`
- **Condiciones**:
  - La programación debe ser para hoy
  - El estado actual debe ser `pending` o `programada`

### 4. Completado de Tarea
- **Cambio**: `in_progress` → `completed`
- **Trigger**: Se marca una tarea como completada (`is_completed = True`)
- **Lógica**: `OrderStatusService.update_order_status_for_task_completion()`

### 5. Desmarcar Tarea como Completada
- **Cambio**: `completed` → `in_progress` o `programada`
- **Trigger**: Se desmarca una tarea como completada (`is_completed = False`)
- **Lógica**: `OrderStatusService.update_order_status_for_task_completion()`
- **Determinación del estado**:
  - Si la tarea se ejecuta hoy: `in_progress`
  - Si la tarea se ejecuta otro día: `programada`

### 6. Reprogramación de Tarea
- **Cambio**: `in_progress` → `programada`
- **Trigger**: Se reprograma una tarea para otro día
- **Lógica**: `OrderStatusService.update_order_status_for_task_reprogramming()`
- **Condiciones**:
  - El estado actual debe ser `in_progress`
  - La nueva fecha debe ser diferente a hoy

### 7. Eliminación de Tarea
- **Cambio**: `programada` o `in_progress` → `pending`
- **Trigger**: Se elimina una tarea
- **Lógica**: `OrderStatusService.update_order_status_for_task_deletion()`
- **Condiciones**:
  - No debe haber otras tareas para el mismo lote

## Endpoints de la API

### Nuevos Endpoints

1. **Sincronizar estado de una orden específica**
   ```
   POST /orders/{order_id}/sync_status
   ```

2. **Sincronizar estado de todas las órdenes**
   ```
   POST /orders/sync_all_status
   ```

3. **Actualizar estados para tareas de hoy**
   ```
   POST /orders/update_status_for_today
   ```

4. **Reprogramar tarea**
   ```
   POST /programmings/{programming_id}/tasks/{task_id}/reprogram
   ```

## Integración en el Frontend

### Servicio de Sincronización

El frontend incluye `orderStatusService` (`frontend/programacionesHermel/src/lib/orderStatusService.ts`) que maneja la sincronización de estados desde el cliente.

### Hooks Actualizados

- `useTaskActions`: Incluye sincronización después de eliminar y duplicar tareas
- `useSchedule`: Maneja la sincronización en operaciones de programación

## Ventajas de la Implementación

### 1. Centralización
- Toda la lógica de cambio de estados está en un solo lugar
- Fácil mantenimiento y debugging
- Consistencia en toda la aplicación

### 2. Automatización
- Los cambios de estado ocurren automáticamente
- No requiere intervención manual
- Reduce errores humanos

### 3. Flexibilidad
- Fácil agregar nuevos estados
- Fácil modificar la lógica de transiciones
- Endpoints para sincronización manual

### 4. Robustez
- Manejo de errores centralizado
- Validaciones de datos
- Logs para debugging

## Casos de Uso

### Escenario 1: Flujo Normal
1. Se crea una orden → Estado: `pending`
2. Se crea una tarea para la orden → Estado: `programada`
3. Se inicia la tarea → Estado: `in_progress`
4. Se completa la tarea → Estado: `completed`

### Escenario 1b: Flujo Directo (sin programación previa)
1. Se crea una orden → Estado: `pending`
2. Se crea una tarea para hoy → Estado: `pending`
3. Se inicia la tarea → Estado: `in_progress`
4. Se completa la tarea → Estado: `completed`

### Escenario 1c: Cambio Automático por Fecha
1. Se crea una orden → Estado: `pending`
2. Se crea una tarea programada para hoy → Estado: `pending`
3. **Automáticamente** cuando es el día de la programación → Estado: `in_progress`
4. Se completa la tarea → Estado: `completed`

### Escenario 2: Reprogramación
1. Tarea en `in_progress`
2. Se reprograma para mañana → Estado: `programada`
3. Se ejecuta mañana → Estado: `in_progress`
4. Se completa → Estado: `completed`

### Escenario 3: Eliminación
1. Tarea en `programada`
2. Se elimina la tarea → Estado: `pending`
3. Se crea nueva tarea → Estado: `programada`

## Testing

### Script de Prueba
Se incluye `test_order_status_flow.py` que prueba todos los escenarios del flujo.

### Ejecución
```bash
cd backend/ApiSchedule
python test_order_status_flow.py
```

## Mantenimiento

### Agregar Nuevos Estados
1. Actualizar `OrderStatus` enum
2. Agregar lógica en `OrderStatusService`
3. Actualizar documentación
4. Agregar tests

### Modificar Transiciones
1. Editar métodos en `OrderStatusService`
2. Verificar consistencia
3. Actualizar tests
4. Actualizar documentación

## Troubleshooting

### Problemas Comunes

1. **Estado no cambia**
   - Verificar que el lote coincida
   - Verificar condiciones de cambio
   - Revisar logs de la aplicación

2. **Error en sincronización**
   - Verificar conectividad con la base de datos
   - Verificar permisos de usuario
   - Revisar logs de errores

3. **Estados inconsistentes**
   - Usar endpoint de sincronización manual
   - Verificar integridad de datos
   - Revisar transacciones de base de datos

### Logs Útiles
- Cambios de estado en `OrderStatusService`
- Errores de sincronización
- Operaciones de tareas
- Transacciones de base de datos
