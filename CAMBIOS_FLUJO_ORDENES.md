# Cambios Implementados para el Nuevo Flujo de Estados de Órdenes

## Resumen del Nuevo Flujo

El nuevo flujo de estados de órdenes funciona de la siguiente manera:

1. **Estado inicial**: `unprogrammed` (sin programar)
2. **Agregar a tarea**: `unprogrammed` → `programmed` (programada)
3. **Cantidad faltante > 0**: `programmed` → `pending` (pendiente)
4. **Cantidad faltante ≤ 0**: `pending` → `completed` (completada)

## Archivos Modificados

### 1. `app/models/state.py`
- **Cambio**: Corregido `unprogammed` → `unprogrammed`
- **Razón**: Error tipográfico en el enum original

### 2. `app/models/order.py`
- **Cambio**: Actualizado valor por defecto a `OrderStatus.unprogrammed`
- **Razón**: Las órdenes nuevas deben empezar sin programar

### 3. `app/utils/order_status_service.py`
- **Nuevos métodos**:
  - `update_order_status_based_on_missing_quantity()`: Maneja cambios de estado basados en cantidad faltante
- **Métodos actualizados**:
  - `update_order_status_for_task_creation()`: Cambia de `unprogrammed` a `programmed`
  - `update_order_status_for_task_deletion()`: Cambia de `programmed` a `unprogrammed`
  - `sync_order_status_for_lote()`: Implementa la nueva lógica de sincronización
- **Métodos simplificados**:
  - Eliminada lógica compleja de `in_progress` ya que no se usa en el nuevo flujo

### 4. `app/api/v1/routes_order.py`
- **Endpoint actualizado**: `PATCH /{order_id}`
  - Ahora incluye lógica automática de cambio de estado cuando se actualiza `missing_quantity`
- **Endpoint actualizado**: `PATCH /{order_id}/status`
  - Agregado rol `WAREHOUSE` a los permisos
  - Incluye `missing_quantity` en la respuesta
- **Nuevo endpoint**: `PATCH /{order_id}/warehouse-fields`
  - Específico para actualizaciones de almacén con cambio automático de estado
- **Endpoint actualizado**: `GET /`
  - Incluye todos los campos nuevos en la respuesta

### 5. `app/schemas/order.py`
- **Esquema actualizado**: `OrderOut`
  - Agregados campos de almacén: `received_user`, `received_date`, `received_quantity`, `missing_quantity`, `submitted_user`, `submitted_date`
- **Esquema corregido**: `OrderWarehouseUpdate`
  - Corregida sintaxis de campos opcionales

## Permisos de Roles

### Roles que pueden actualizar órdenes:
- **ADMIN**: Todos los permisos
- **PLANNER**: Todos los permisos  
- **SUPERVISOR**: Todos los permisos
- **WAREHOUSE**: Puede actualizar campos de almacén y estados

### Roles sin permisos:
- **USER**: No puede actualizar órdenes ni cambiar estados

## Nuevos Endpoints

### `PATCH /orders/{order_id}/warehouse-fields`
- **Propósito**: Actualización específica para campos de almacén
- **Funcionalidad**: Cambio automático de estado basado en `missing_quantity`
- **Permisos**: ADMIN, PLANNER, SUPERVISOR, WAREHOUSE
- **Respuesta**: Incluye información sobre cambio de estado

## Migración de Base de Datos

### Archivo: `alembic/versions/update_order_status_enum_fix_unprogrammed.py`
- Corrige el enum `OrderStatus` con los valores correctos
- Actualiza registros existentes para usar los nuevos valores
- Establece `unprogrammed` como valor por defecto

## Archivo de Pruebas

### `test_new_order_flow.py`
- Prueba completa del flujo de estados
- Verificación de cambios automáticos de estado
- Prueba de sincronización de estados
- Validación de permisos de roles

## Cómo Usar el Nuevo Flujo

### 1. Crear Orden
```python
# La orden se crea automáticamente con estado 'unprogrammed'
order = Order(lote=123, code="ABC", ...)
```

### 2. Agregar a Tarea
```python
# Al crear una tarea, el estado cambia automáticamente a 'programmed'
task = Task(lote="123", ...)
OrderStatusService.update_order_status_for_task_creation(db, task)
```

### 3. Actualizar Cantidad Faltante
```python
# Al actualizar missing_quantity, el estado cambia automáticamente
order.missing_quantity = 10  # > 0 → estado 'pending'
OrderStatusService.update_order_status_based_on_missing_quantity(db, order)

order.missing_quantity = 0   # ≤ 0 → estado 'completed'
OrderStatusService.update_order_status_based_on_missing_quantity(db, order)
```

### 4. Usar Endpoint de Almacén
```bash
# PATCH /orders/123/warehouse-fields
{
  "received_quantity": 90,
  "missing_quantity": 10,
  "received_user": "warehouse_user"
}
# El estado cambia automáticamente a 'pending'
```

## Validación

Para verificar que todo funciona correctamente:

1. Ejecutar el script de pruebas: `python test_new_order_flow.py`
2. Aplicar la migración de base de datos cuando esté disponible
3. Probar los endpoints con diferentes roles
4. Verificar que los cambios de estado son automáticos según las reglas del negocio

## Beneficios del Nuevo Flujo

1. **Automatización**: Los cambios de estado son automáticos basados en reglas de negocio
2. **Simplicidad**: Flujo más claro y fácil de entender
3. **Consistencia**: Estados siempre reflejan el estado real de la orden
4. **Permisos**: Control granular sobre quién puede hacer qué
5. **Trazabilidad**: Campos de auditoría para seguimiento de cambios