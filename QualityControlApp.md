# Documentación Backend - Proyecto Frontend QualityControl

Este documento detalla **únicamente** los endpoints y flujos del backend que son consumidos actualmente por el proyecto `frontend/QualityControl`.

## Autenticación
Gestionado por `use-auth.ts` y `auth-service.ts`.

| Método | Endpoint | Descripción | Uso en Frontend |
|--------|----------|-------------|-----------------|
| `POST` | `/auth/login` | Iniciar sesión | `use-auth.ts`: Autenticación de usuario. Recibe `username` y `password` (form-data). |
| `POST` | `/auth/logout` | Cerrar sesión | `use-auth.ts`: Finaliza la sesión del usuario. |

---

## Catálogo de Pruebas (Catalog Tests)
Gestión del maestro de pruebas de calidad que se pueden aplicar a los códigos.

| Método | Endpoint | Descripción | Uso en Frontend |
|--------|----------|-------------|-----------------|
| `GET` | `/catalog_tests/` | Listar pruebas | `catalog-test-service.ts`: Obtiene todas las pruebas del catálogo. |
| `POST` | `/catalog_tests/` | Crear prueba | `catalog-test-service.ts`: Agrega una nueva prueba con sus preguntas. |
| `PATCH` | `/catalog_tests/{id}` | Actualizar prueba | `catalog-test-service.ts`: Modifica una prueba y sincroniza preguntas. |
| `DELETE` | `/catalog_tests/{id}` | Eliminar prueba | `catalog-test-service.ts`: Elimina una prueba del catálogo. |

---

## Códigos y Vinculación de Pruebas
Relación entre los códigos de producto y las pruebas de calidad requeridas.

| Método | Endpoint | Descripción | Uso en Frontend |
|--------|----------|-------------|-----------------|
| `GET` | `/codes/production` | Listar productos | `code-service.ts`: Obtiene códigos con filtro de búsqueda. |
| `POST` | `/codes/{id}/tests` | Sincronizar pruebas | `code-service.ts`: Vincula/desvincula pruebas a un código. |
| `GET` | `/codes/{id}/tests` | Listar vinculadas | `code-service.ts`: Obtiene pruebas asociadas y sus instrucciones. |
| `GET` | `/codes/by_code_string/{code}/tests` | Listar por código | `code-service.ts`: Busca pruebas usando el string del código. |
| `DELETE` | `/codes/{id}/tests/{tid}` | Desvincular prueba | `code-service.ts`: Elimina vínculo individual. |

---

## Resultados de Pruebas de Calidad (QC Tests)
Registro de resultados de inspección y gestión de estados (pendientes, aprobados, etc.).

| Método | Endpoint | Descripción | Uso en Frontend |
|--------|----------|-------------|-----------------|
| `POST` | `/qctest/session` | Guardar sesión | `quality-test-service.ts`: Registra resultados y metadata para un lote. |
| `PATCH` | `/qctest/session/{id}/status` | Cambiar estado | `quality-test-service.ts`: Aprueba o rechaza una sesión de pruebas. |
| `GET` | `/qctest/session/{lote}/{code_id}` | Obtener sesión | `quality-test-service.ts`: Recupera resultados con firmas y detalles. |
| `GET` | `/test_record/` | Listar registros | `test-record-service.ts`: Dashboard de inspecciones realizadas. |
| `PATCH` | `/test_record/{id}` | Editar registro | `test-record-service.ts`: Actualiza comentarios o estado individual. |
| `GET` | `/qctest/{lote}` | Consulta rápida | (Legacy) Recupera el último registro de un lote. |

---

## Manual de Calidad
Gestión del manual instructivo y ayuda contextual por sección.

| Método | Endpoint | Descripción | Uso en Frontend |
|--------|----------|-------------|-----------------|
| `POST` | `/manual` | Guardar manual | `manual-service.ts`: Crea/Actualiza revisión completa. |
| `POST` | `/manual/identity` | Crear identidad | `manual-service.ts`: Registra un nuevo nombre de manual. |
| `GET` | `/manual/list` | Listar nombres | `manual-service.ts`: Lista nombres únicos de manuales. |
| `GET` | `/manual/identities` | Listar IDs | `manual-service.ts`: Lista parejas ID/Nombre. |
| `GET` | `/manual/hierarchy` | Ver jerarquía | `manual-service.ts`: Estructura completa (capítulos/pruebas). |
| `GET` | `/manual/section/{name}` | Ayuda contextual | `ManualHelpSheet.tsx`: Contenido de una sección específica. |
| `GET` | `/manual/{id}/full-content` | Manual completo | `ManualHelpSheet.tsx`: Versión agregada para impresión/lectura. |
| `GET` | `/manual/latest` | Última revisión | `manual-service.ts`: Información de la revisión más reciente. |
| `POST` | `/manual/{id}/chapters` | Crear capítulo | `manual-service.ts`: Agrega capítulos individualmente. |
| `DELETE` | `/manual/{name}` | Eliminar manual | `manual-service.ts`: Borra identidad y revisiones. |

---

## Notas de Implementación

1. **Gestión de Sesión**:
   - A diferencia de otros proyectos, este utiliza `sessionStorage` en lugar de `localStorage` para persistir la sesión (`hermel_auth`).

2. **Generación de PDF**:
   - Se realiza enteramente en el lado del cliente utilizando `jspdf` y `html2canvas` dentro de `pdf-service.ts`. No consume endpoints específicos de generación de PDF en el backend.

3. **Interperceptores**:
   - `api.ts` maneja automáticamente el envío del token `Bearer` y detecta errores `401` para disparar el evento de sesión expirada.
