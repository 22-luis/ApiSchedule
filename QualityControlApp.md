# Documentación Backend - Proyecto Frontend QualityControl

Este documento detalla **únicamente** los endpoints y flujos del backend que son consumidos actualmente por el proyecto `frontend/QualityControl`.

## 🔐 Autenticación
Gestionado por `use-auth.ts` y `auth-service.ts`.

| Método | Endpoint | Descripción | Uso en Frontend |
|--------|----------|-------------|-----------------|
| `POST` | `/auth/login` | Iniciar sesión | `use-auth.ts`: Autenticación de usuario. Recibe `username` y `password` (form-data). |
| `POST` | `/auth/logout` | Cerrar sesión | `use-auth.ts`: Finaliza la sesión del usuario. |

---

## 🧪 Catálogo de Pruebas (Catalog Tests)
Gestión del maestro de pruebas de calidad que se pueden aplicar a los códigos.

| Método | Endpoint | Descripción | Uso en Frontend |
|--------|----------|-------------|-----------------|
| `GET` | `/catalog_tests/` | Listar pruebas | `catalog-test-service.ts`: Obtiene todas las pruebas del catálogo. |
| `POST` | `/catalog_tests/` | Crear prueba | `catalog-test-service.ts`: Agrega una nueva prueba al catálogo. |
| `PATCH` | `/catalog_tests/{id}` | Actualizar prueba | `catalog-test-service.ts`: Modifica una prueba existente. |
| `DELETE` | `/catalog_tests/{id}` | Eliminar prueba | `catalog-test-service.ts`: Elimina una prueba del catálogo. |

---

## 🏷️ Códigos y Vinculación de Pruebas
Relación entre los códigos de producto y las pruebas de calidad requeridas.

| Método | Endpoint | Descripción | Uso en Frontend |
|--------|----------|-------------|-----------------|
| `GET` | `/codes/production` | Listar productos | `code-service.ts`: Obtiene códigos con filtro de búsqueda y paginación. |
| `POST` | `/codes/{id}/tests/` | Vincular pruebas | `code-service.ts`: Asocia múltiples pruebas del catálogo a un código. |
| `DELETE` | `/codes/{id}/tests/{tid}` | Desvincular prueba | `code-service.ts`: Elimina la asociación entre un código y una prueba. |
| `GET` | `/codes/{id}/tests` | Listar vinculadas | `code-service.ts`: Obtiene las pruebas asociadas a un código específico. |

---

## 📋 Resultados de Pruebas de Calidad (QC Tests)
Registro de los resultados obtenidos tras realizar las pruebas.

| Método | Endpoint | Descripción | Uso en Frontend |
|--------|----------|-------------|-----------------|
| `POST` | `/qctest` | Guardar resultados | `quality-test-service.ts`: Registra los resultados de las pruebas para un lote. |
| `PATCH` | `/qctest/{id}` | Actualizar resultados | `quality-test-service.ts`: Modifica registros previos de pruebas. |
| `GET` | `/qctest/{lote}` | Consultar resultados | `quality-test-service.ts`: Recupera los resultados registrados para un lote específico. |

---

## 📖 Manual de Calidad
Gestión del manual instructivo de control de calidad.

| Método | Endpoint | Descripción | Uso en Frontend |
|--------|----------|-------------|-----------------|
| `POST` | `/manual` | Crear/Actualizar | `manual-service.ts`: Sube contenido HTML para generar el manual. |
| `GET` | `/manual/latest` | Obtener último | `manual-service.ts`: Descarga la versión más reciente del manual completo. |
| `GET` | `/manual/chapters` | Listar capítulos | `manual-service.ts`: Obtiene la lista de capítulos y secciones disponibles. |
| `GET` | `/manual/section/{name}` | Obtener sección | `manual-service.ts`: Recupera una sección específica por su nombre. |

---

## ⚖️ Notas de Implementación

1. **Gestión de Sesión**:
   - A diferencia de otros proyectos, este utiliza `sessionStorage` en lugar de `localStorage` para persistir la sesión (`hermel_auth`).

2. **Generación de PDF**:
   - Se realiza enteramente en el lado del cliente utilizando `jspdf` y `html2canvas` dentro de `pdf-service.ts`. No consume endpoints específicos de generación de PDF en el backend.

3. **Interperceptores**:
   - `api.ts` maneja automáticamente el envío del token `Bearer` y detecta errores `401` para disparar el evento de sesión expirada.
