# Ejemplos de Uso - Endpoints de Cálculos

Este documento muestra cómo usar los nuevos endpoints de cálculos que centralizan la lógica de negocio anteriormente ubicada en el frontend.

## 🧮 Endpoints Disponibles

### 1. Calcular Duración de Tarea

#### POST `/api/v1/calculations/task-duration`
Calcula la duración completa de una tarea con información detallada.

**Request:**
```json
{
  "quantity": 100,
  "productivity": 0.5,
  "people": 2
}
```

**Response:**
```json
{
  "minutes": 1500,
  "hours": 25.0,
  "formula_used": "(100 × 0.5 × 60) ÷ 2 = 1500 minutos"
}
```

#### GET `/api/v1/calculations/task-duration/simple?quantity=100&productivity=0.5&people=2`
Versión simplificada que retorna solo los minutos.

**Response:**
```json
{
  "minutes": 1500
}
```

### 2. Obtener Horas de Trabajo

#### GET `/api/v1/calculations/working-hours/2024-01-15`
Obtiene las horas de trabajo para una fecha específica.

**Response:**
```json
{
  "start_hour": 7,
  "start_minute": 0,
  "end_hour": 17,
  "end_minute": 0,
  "is_working_day": true,
  "total_hours": 10.0
}
```

### 3. Calcular Hora Base de Programación

#### GET `/api/v1/calculations/programming-base-time/2024-01-15`
Calcula la hora base de programación para una fecha.

**Response:**
```json
{
  "base_time": "2024-01-15T07:00:00",
  "is_working_day": true
}
```

### 4. Calcular Tiempos Secuenciales

#### POST `/api/v1/calculations/sequential-times`
Calcula tiempos secuenciales para una lista de tareas.

**Request:**
```json
{
  "base_date": "2024-01-15",
  "base_time": "07:00",
  "tasks": [
    {"id": "1", "description": "Tarea 1", "minutes": 60},
    {"id": "2", "description": "Tarea 2", "minutes": 90},
    {"id": "3", "description": "Tarea 3", "minutes": 120}
  ]
}
```

**Response:**
```json
{
  "base_date": "2024-01-15",
  "base_time": "07:00",
  "tasks": [
    {
      "id": "1",
      "description": "Tarea 1",
      "minutes": 60,
      "start_time": "2024-01-15T07:00:00",
      "end_time": "2024-01-15T08:00:00"
    },
    {
      "id": "2",
      "description": "Tarea 2",
      "minutes": 90,
      "start_time": "2024-01-15T08:00:00",
      "end_time": "2024-01-15T09:30:00"
    },
    {
      "id": "3",
      "description": "Tarea 3",
      "minutes": 120,
      "start_time": "2024-01-15T09:30:00",
      "end_time": "2024-01-15T11:30:00"
    }
  ]
}
```

### 5. Validar Parámetros

#### POST `/api/v1/calculations/validate-task-parameters?quantity=100&productivity=0.5&people=2`
Valida los parámetros de una tarea.

**Response:**
```json
{
  "is_valid": true,
  "errors": [],
  "warnings": []
}
```

### 6. Información de Fórmulas

#### GET `/api/v1/calculations/formula-info`
Obtiene información sobre las fórmulas utilizadas.

**Response:**
```json
{
  "task_duration_formula": {
    "description": "Fórmula para calcular duración de tareas",
    "formula": "minutos = (cantidad × productividad × 60) ÷ personas",
    "variables": {
      "cantidad": "Número de unidades a producir",
      "productividad": "Tiempo por unidad (en horas)",
      "personas": "Número de personas asignadas",
      "minutos": "Duración calculada (redondeada hacia arriba)"
    },
    "example": {
      "cantidad": 100,
      "productividad": 0.5,
      "personas": 2,
      "resultado": "minutos = (100 × 0.5 × 60) ÷ 2 = 1500 minutos"
    }
  },
  "working_hours": {
    "description": "Horarios de trabajo configurados",
    "monday_friday": "7:00 - 17:00",
    "saturday": "7:30 - 17:30",
    "sunday": "No laboral"
  }
}
```

## 🔄 Migración desde Frontend

### Antes (Frontend):
```typescript
// useTaskForm.ts
function calcularMinutos(cantidad: number, productividad: number, personas: number): number {
  if (!cantidad || !productividad || !personas || personas < 1) return 0;
  const minutos = (cantidad * productividad * 60) / personas;
  return Math.ceil(minutos);
}

// Uso
const minutes = calcularMinutos(100, 0.5, 2);
```

### Después (Frontend):
```typescript
// useTaskForm.ts
const calculateTaskMinutes = async (quantity: number, productivity: number, people: number): Promise<number> => {
  try {
    const response = await api.get('/calculations/task-duration/simple', {
      params: { quantity, productivity, people }
    });
    return response.data.minutes;
  } catch (error) {
    console.error('Error calculando minutos:', error);
    return 0;
  }
};

// Uso
const minutes = await calculateTaskMinutes(100, 0.5, 2);
```

## 🛡️ Seguridad y Permisos

- **Todos los endpoints** requieren autenticación
- **Cálculo de tiempos secuenciales** requiere roles: `admin`, `planner`, o `supervisor`
- **Validación de parámetros** se realiza en el backend
- **Manejo de errores** centralizado con mensajes descriptivos

## 🧪 Testing

Puedes probar los endpoints usando curl:

```bash
# Calcular duración de tarea
curl -X POST "http://localhost:8000/api/v1/calculations/task-duration" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"quantity": 100, "productivity": 0.5, "people": 2}'

# Obtener horas de trabajo
curl -X GET "http://localhost:8000/api/v1/calculations/working-hours/2024-01-15" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 📈 Beneficios de la Migración

1. **Centralización**: Una sola fuente de verdad para las fórmulas
2. **Consistencia**: Mismos cálculos en toda la aplicación
3. **Mantenibilidad**: Cambios en fórmulas solo requieren actualizar el backend
4. **Testabilidad**: Más fácil escribir tests unitarios
5. **Seguridad**: Lógica de negocio protegida en el servidor
6. **Rendimiento**: Cálculos complejos en el servidor
7. **Reutilización**: Otros clientes pueden usar los mismos cálculos
