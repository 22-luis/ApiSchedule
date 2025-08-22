# Ejemplo de Uso del Endpoint de Programaciones Disponibles

## Endpoint: `GET /api/v1/programmings/team/{team_uuid}/available`

Este endpoint devuelve las programaciones con estado 'available' para un equipo específico, desde la fecha actual hacia adelante.

### Ejemplo 1: Obtener programaciones disponibles existentes

```bash
curl -X GET "http://localhost:8000/api/v1/programmings/team/123e4567-e89b-12d3-a456-426614174000/available" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Respuesta esperada:**
```json
{
  "team_id": "123e4567-e89b-12d3-a456-426614174000",
  "team_name": "Equipo Fabricado 1",
  "available_programmings": [
    {
      "id": "987fcdeb-51a2-43d1-9f12-345678901234",
      "team_name": "Equipo Fabricado 1",
      "date": "2024-01-15"
    },
    {
      "id": "456abcde-78f9-0123-4567-89abcdef0123",
      "team_name": "Equipo Fabricado 1",
      "date": "2024-01-16"
    }
  ]
}
```

### Ejemplo 2: Cuando no hay programaciones futuras (crea automáticamente)

Si no existen programaciones futuras disponibles, el sistema automáticamente crea una nueva programación.

**Respuesta esperada:**
```json
{
  "team_id": "123e4567-e89b-12d3-a456-426614174000",
  "team_name": "Equipo Molino 2",
  "available_programmings": [
    {
      "id": "789def01-2345-6789-abcd-ef0123456789",
      "team_name": "Equipo Molino 2",
      "date": "2024-01-16"
    }
  ]
}
```

### Ejemplo 3: Error - Equipo no encontrado

```bash
curl -X GET "http://localhost:8000/api/v1/programmings/team/00000000-0000-0000-0000-000000000000/available" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Respuesta esperada:**
```json
{
  "detail": "Team not found"
}
```

### Ejemplo 4: Error - Sin autorización

```bash
curl -X GET "http://localhost:8000/api/v1/programmings/team/123e4567-e89b-12d3-a456-426614174000/available"
```

**Respuesta esperada:**
```json
{
  "detail": "Not authenticated"
}
```

## Comportamiento del Endpoint

### Características principales:

1. **Filtrado por fecha**: Solo devuelve programaciones desde la fecha actual hacia adelante
2. **Filtrado por estado**: Solo devuelve programaciones con estado 'available'
3. **Creación automática**: Si no hay programaciones futuras, crea una nueva programación
4. **Ordenamiento**: Las programaciones se devuelven ordenadas por fecha
5. **Control de acceso**: Verifica permisos del usuario

### Lógica de creación automática:

- Si no hay programaciones futuras disponibles:
  - Busca la última programación del equipo
  - Si existe una última programación, crea una nueva para el día siguiente
  - Si no existe ninguna programación, crea una para mañana
  - La nueva programación se crea con estado 'available'

### Permisos requeridos:

- **Admin/Planner/Supervisor**: Pueden acceder a cualquier equipo
- **Usuario regular**: Solo puede acceder a equipos a los que pertenece

## Uso en JavaScript/Frontend

```javascript
// Función para obtener programaciones disponibles
async function getAvailableProgrammings(teamId, token) {
  try {
    const response = await fetch(`/api/v1/programmings/team/${teamId}/available`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data.available_programmings;
  } catch (error) {
    console.error('Error obteniendo programaciones disponibles:', error);
    throw error;
  }
}

// Ejemplo de uso
const teamId = '123e4567-e89b-12d3-a456-426614174000';
const token = 'your_jwt_token';

getAvailableProgrammings(teamId, token)
  .then(programmings => {
    console.log('Programaciones disponibles:', programmings);
    // programmings es un array con las programaciones disponibles
  })
  .catch(error => {
    console.error('Error:', error);
  });
```

## Uso en Python

```python
import requests

def get_available_programmings(team_id, token, base_url="http://localhost:8000"):
    """
    Obtiene las programaciones disponibles para un equipo específico
    """
    url = f"{base_url}/api/v1/programmings/team/{team_id}/available"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error obteniendo programaciones: {e}")
        raise

# Ejemplo de uso
team_id = "123e4567-e89b-12d3-a456-426614174000"
token = "your_jwt_token"

try:
    result = get_available_programmings(team_id, token)
    print("Programaciones disponibles:", result["available_programmings"])
except Exception as e:
    print(f"Error: {e}")
```
