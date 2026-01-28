# Sistema de Control de Calidad (Arquitectura Híbrida)

## 1. Visión General
Este módulo gestiona el control de calidad mediante un enfoque **híbrido (SQL + NoSQL)**, priorizando la flexibilidad en la gestión documental de manuales y la integridad en la ejecución de pruebas.

### Características Clave
- **Manual Flexible**: El manual de calidad se almacena como un documento versionado (JSON), permitiendo estructuras libres y edición rica.
- **Vinculación Dinámica**: Las pruebas se vinculan a los capítulos del manual mediante referencias textuales validadas.
- **Ejecución Estricta**: Aunque la definición es flexible, la ejecución y aprobación de pruebas sigue un **flujo de estados estricto** con validación de roles.

---

## 2. Guía de Integración Frontend
Esta sección detalla cómo deben las aplicaciones cliente consumir los servicios para garantizar la integridad de los datos.

### 2.1 Módulo: Editor de Manuales
El frontend es responsable de generar la estructura JSON correcta antes de enviarla.

**Flujo:**
1. **Carga Inicial**: `GET /manual/latest`.
   - Si devuelve 404, inicializar editor vacío.
2. **Edición**: El editor debe permitir crear jerarquías (Capítulos).
   - **Importante**: El backend espera que el contenido HTML final sea parseable. Se recomienda usar etiquetas `<h1>` para identificar los Capítulos Principales.
3. **Guardado**: `POST /manual/`.
   - Enviar el objeto JSON/HTML completo.
   - El backend procesará automáticamente los `<h1>` para registrar los capítulos válidos.

### 2.2 Módulo: Catálogo de Pruebas
Para crear una prueba vinculada correctamente, el frontend **DEBE** asegurarse de que el usuario seleccione un capítulo existente.

**Flujo de Creación:**
1. **Obtener Capítulos**: `GET /manual/chapters`.
   - Devuelve: `{ "chapters": ["Capitulo 1", "Capitulo 2", ...] }`.
2. **Formulario UI**:
   - El campo "Chapter" debe ser un **Autocomplete/Select** alimentado por la lista anterior.
   - **No permitir texto libre** (o advertir que si no coincide, fallará).
3. **Envío**: `POST /catalog_tests/`.
   - Payload: `{ "name": "...", "chapter": "Nombre Exacto", ... }`.
   - Si el capítulo no coincide exactamente con uno del manual vigente -> **Error 400**.

### 2.3 Módulo: Ejecución de Pruebas (Operador)
El ciclo de vida de una prueba es: `undone` -> `pending` -> `done` -> `accepted`.

**Flujo:**
1. **Buscar Lote**: Al entrar a un lote, consultar si ya existe registro: `GET /qctest/{lote}`.
2. **Iniciar**:
   - Si es 404 -> `POST /qctest/` con `status: "pending"`.
3. **Guardar Respuestas**:
   - `PATCH /qctest/{id}`.
   - Enviar `answer: { "preg_id": "valor", ... }`.
   - Se puede guardar parcialmente.
4. **Finalizar**:
   - Al terminar todas las preguntas, usuario da click en "Finalizar".
   - `PATCH /qctest/{id}` con `status: "done"`.

### 2.4 Módulo: Aprobación (Coordinador)
Solo los coordinadores ven el botón de aprobación.

**Flujo:**
1. **Visualización**: El frontend renderiza las respuestas del registro status `done`.
2. **Acción**:
   - Si el usuario logueado tiene rol `QC_COORDINATOR`, habilitar botón "Aprobar".
   - Si no, mostrar "Pendiente de revisión" (readonly).
3. **Envío**:
   - `PATCH /qctest/{id}` con `status: "accepted"`.
   - Backend valida rol y estampa firma de tiempo.

---

## 3. Modelo de Datos (Referencia)

### `QcManual`
Almacena versiones completas del manual.
- `version`: Integer (incremental)
- `content`: **JSONB** (Contiene la estructura completa).

### `CatalogTest`
Define qué pruebas existen.
- `chapter`: **String**. Debe coincidir con un `<h1>` del manual.

### `TestRecord`
Registra la ejecución.
- `lote`: Integer (FK a Producción)
- `status`: Enum (`undone`, `pending`, `done`, `accepted`)
- `answer`: **JSONB** (Respuestas).

---

## 4. Endpoints Principales

### Manuales
- `POST /manual/`: Crear versión.
- `GET /manual/latest`: Ver manual.
- `GET /manual/chapters`: **Dropdown de capítulos**.

### Pruebas (Catálogo)
- `POST /catalog_tests/`: Crear prueba (**Valida capítulo**).
- `PATCH /catalog_tests/{id}`: Editar.

### Ejecución
- `POST /qctest/`: Iniciar.
- `PATCH /qctest/{id}`: Guardar avance / Finalizar / Aprobar.
