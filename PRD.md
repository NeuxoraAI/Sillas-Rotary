# PRD v2 — Sistema Integral de Gestión Social y Técnica

**Proyecto**: Ecosistema VIDA UG — Programa de Donación de Sillas de Ruedas  
**Desarrollado por**: NEUXORA · C-MED  
**Versión**: 2.0  
**Fecha**: 2026-04-18  
**Estado**: Aprobado para implementación

---

## 1. Resumen Ejecutivo

El sistema actual es un formulario básico de registro (login → estudio socioeconómico → solicitud técnica) sin gestión real de usuarios, sin seguimiento post-registro y sin soporte multi-región. 

El PRD v2 transforma esta herramienta en una **plataforma de gestión global** que soporta:

1. **Regiones globales** con catálogo administrado jerárquicamente por país.
2. **Auto-llenado inteligente** dentro del formulario para agilizar el trabajo del capturista.
3. **Panel de consulta** con filtros, búsqueda y exportación a Excel.
4. **Seguimiento del armado** de la silla con estados, auditoría y notificaciones al beneficiario.
5. **Sistema de autenticación real** para capturistas, técnicos y administradores.
6. **Corrección de bugs** existentes (foto no se guarda en DB, captura de foto en el momento).

---

## 2. Stack Tecnológico

| Capa | Tecnología | Notas |
|------|-----------|-------|
| Frontend | HTML5, Tailwind CSS, Vanilla JS | Mobile-first. Fetch API al backend |
| Backend | Python (FastAPI) | API RESTful, lógica de negocio, comunicación con Supabase |
| Base de Datos | Supabase (PostgreSQL) | Almacenamiento relacional. La DB actual se limpiará (datos de prueba) |
| Almacenamiento | Supabase Storage | Fotos de pacientes (PNG/JPG) |
| Deploy | Vercel | Frontend + Backend (serverless functions) |
| Notificaciones | Twilio / WhatsApp Business API (SMS) + Resend / SMTP (Email) | Para alertas de silla lista |

> **Nota**: El backend local con SQLite (`sillas.db`) está deprecado. Solo se usa Supabase PostgreSQL.

---

## 3. Tipos de Usuario y Roles

| Rol | Descripción | Permisos |
|-----|-------------|----------|
| **Administrador** | Gestiona el catálogo de regiones, da de alta capturistas y técnicos | CRUD regiones, CRUD usuarios, acceso total al panel, exportación |
| **Capturista** | Personal de campo que realiza entrevistas y registros | Crear/editar registros, consultar panel (solo lectura), exportar a Excel |
| **Técnico** | Personal que arma las sillas de ruedas | Cambiar estado de armado de sillas, ver panel de seguimiento |

### 3.1 Sistema de Autenticación

El login actual (solo nombre) se reemplaza por un **sistema de autenticación real**:

- El **Administrador** da de alta a los capturistas y técnicos en el sistema.
- Cada usuario tiene: `nombre`, `email`, `rol`, `contraseña` (hasheada).
- Sesiones basadas en JWT almacenado en `localStorage` con expiración configurable.
- El login valida credenciales contra la tabla `usuarios` en Supabase.

---

## 4. Módulos del Sistema

### Módulo 1: Autenticación y Gestión de Usuarios

#### 4.1.1 Login (`login.html`)

- **Campos**: Email + Contraseña.
- **Comportamiento**: Valida contra tabla `usuarios`. Genera JWT. Redirige según rol:
  - Administrador → Panel de administración.
  - Capturista → Selección de región → Formulario de registro.
  - Técnico → Panel de seguimiento de armado.

#### 4.1.2 Alta de Usuarios (Solo Administrador)

- **Pantalla**: Sección dentro del panel de administración.
- **Campos**: Nombre completo, email, rol (capturista/técnico/admin), contraseña temporal.
- **Comportamiento**: El admin crea al usuario. Al primer login, el usuario puede cambiar su contraseña.

---

### Módulo 2: Sistema de Regiones

#### 4.2.1 Catálogo de Regiones (Admin)

Las regiones son un concepto a **nivel de evento/jornada**. Representan dónde se realiza la campaña de donación.

**Estructura jerárquica**:

```
País → Región (formato libre por país)
```

**Ejemplos**:

| País | Región | Código Corto |
|------|--------|--------------|
| México | León, Gto | LON |
| México | Irapuato, Gto | IRA |
| USA | Pearland, TX | PRL |
| USA | Houston, TX | HOU |
| Colombia | Bogotá, D.C. | BOG |

- El **formato de la región varía por país** pero se mantiene consistente dentro de cada país.
- Cada región tiene un **código corto** (3 letras) usado para generar el ID del beneficiario.
- El campo `sede` se mantiene como **texto libre** (ej: "León sede Forum", "Irapuato sede DIF").

#### 4.2.2 CRUD de Regiones

- **Crear**: Admin define país, nombre de región y código corto.
- **Editar**: Solo nombre descriptivo (el código corto NO se edita una vez creado, porque afectaría IDs existentes).
- **Desactivar**: No se elimina, se desactiva para preservar integridad referencial.

#### 4.2.3 Selección de Región en el Flujo de Registro

Antes de iniciar un registro, el capturista:

1. Selecciona el **país** (dropdown).
2. Selecciona la **región** (dropdown filtrado por país).
3. Escribe la **sede** (texto libre).

Estos valores se almacenan en la sesión y se pre-llenan en todos los registros subsecuentes durante esa jornada.

---

### Módulo 3: Estudio Socioeconómico (`socioeconomico.html`)

#### 4.3.1 Datos del Beneficiario

Sin cambios en los campos actuales:
- Nombre completo, fecha de nacimiento, diagnóstico médico.
- Dirección: calle, colonia, ciudad.
- Teléfonos de contacto.

**NUEVO — Email del beneficiario o tutor** (opcional): Para notificaciones por correo.

#### 4.3.2 Auto-llenado Inteligente

**Problema que resuelve**: Cuando el capturista llena un dato en una sección del formulario, si ese mismo dato aparece en otra sección o campo relacionado, debe completarse automáticamente.

**Comportamiento**:

- **Dentro del mismo formulario**: Si un campo se repite conceptualmente (ej: nombre del beneficiario aparece tanto en sección de datos como en resumen), se sincroniza en tiempo real con event listeners.
- **Campos de la sesión (región, sede, fecha, capturista)**: Se auto-llenan desde la selección inicial de la jornada. El capturista NO tiene que escribir la sede o la fecha del estudio en cada registro.
- **Validación de duplicados**: Al escribir el nombre del beneficiario + fecha de nacimiento, el sistema busca en la DB si ya existe. Si ya está registrado, muestra un aviso claro: *"Este beneficiario ya fue registrado el [fecha]. No se puede duplicar el registro."*

#### 4.3.3 Datos de los Tutores

Sin cambios estructurales. Se mantienen Tutor 1 y Tutor 2.

**NUEVO**: Campo de **correo electrónico** del tutor (opcional) — Para enviar notificaciones sobre el estado de la silla.

#### 4.3.4 Cierre del Estudio

- Otras fuentes de ingreso, monto, silla previa.
- Elaboró estudio (auto-llenado con nombre del capturista logueado).
- Fecha del estudio (auto-llenado con fecha actual).
- Sede (auto-llenado desde selección de jornada).

---

### Módulo 4: Solicitud Técnica (`tecnica.html`)

Sin cambios en los campos de la solicitud (entorno, capacidad postural, medidas, donación).

#### 4.4.1 Corrección de Bug: Fotografía

**Bug actual**: La foto se sube pero no se refleja correctamente en la DB.

**Corrección**:
- Verificar que el endpoint `/api/upload-foto` retorna la URL pública correcta del bucket de Supabase.
- Verificar que `foto_url` se guarda en la columna `foto_url` de `solicitudes_tecnicas`.
- Agregar preview de la imagen subida antes de enviar el formulario.

#### 4.4.2 NUEVA: Captura de Foto en el Momento

- **Botón "Tomar Foto"**: Usa la API `navigator.mediaDevices.getUserMedia()` para acceder a la cámara del dispositivo.
- **Flujo**: Clic en "Tomar Foto" → Se abre visor de cámara → Captura → Preview → Confirmar o retomar.
- **Compatibilidad**: Mobile-first (cámara trasera por defecto en móviles).
- **Formato de salida**: JPG comprimido (max 10MB).

---

### Módulo 5: ID de Beneficiario

El ID serial actual (`1, 2, 3...`) se reemplaza por un **ID con formato estructurado**.

#### 4.5.1 Formato del ID

```
{PAÍS}-{CÓDIGO_REGIÓN}-{AÑO}-{NÚMERO_SECUENCIAL}
```

**Ejemplos**:

| ID | Significado |
|----|-------------|
| `MX-LON-2026-001` | México, León, año 2026, beneficiario #1 |
| `MX-IRA-2026-015` | México, Irapuato, año 2026, beneficiario #15 |
| `US-PRL-2026-003` | USA, Pearland, año 2026, beneficiario #3 |

#### 4.5.2 Reglas de Generación

- El **número secuencial** es único por combinación `país + región + año`.
- Se genera automáticamente al crear el registro (no editable).
- Se usa un **contador** en la tabla `region_counters` que garantiza secuencia sin gaps.
- El ID se almacena como columna `folio` en la tabla `beneficiarios`.
- El `id` serial de PostgreSQL se mantiene como PK interna (pero el usuario solo ve el `folio`).

---

### Módulo 6: Panel de Registros

#### 4.6.1 Acceso

- Todos los **capturistas** y **administradores** tienen acceso.
- El panel es **solo lectura** (consulta).
- Acceso desde el menú principal después del login.

#### 4.6.2 Pantalla: `panel.html`

**Vista de tabla** con las siguientes columnas:

| Columna | Descripción |
|---------|-------------|
| Folio (ID) | ID estructurado (MX-LON-2026-001) |
| Nombre Beneficiario | Nombre completo |
| Región | País + Región |
| Sede | Texto libre de la sede |
| Fecha de Registro | Fecha del estudio socioeconómico |
| Estado de Silla | Badge visual (Registrada / En proceso / Lista / Entregada) |
| Capturista | Nombre de quien registró |

#### 4.6.3 Filtros

- **País**: Dropdown con todos los países registrados.
- **Región**: Dropdown filtrado por país seleccionado.
- **Estado de silla**: Multi-select (Registrada, En proceso, lista, Entregada).
- **Búsqueda libre**: Por nombre del beneficiario O por folio (ID).
- **Rango de fechas**: Desde - Hasta.

#### 4.6.4 Exportación a Excel

- Botón "Exportar a Excel" que genera un archivo `.xlsx` con los registros filtrados.
- Incluye TODOS los campos del estudio socioeconómico + solicitud técnica.
- Se genera en el frontend usando una librería como `SheetJS (xlsx)`.

#### 4.6.5 Vista de Detalle

Al hacer clic en una fila, se abre un **modal o pantalla de detalle** que muestra:
- Todos los datos del estudio socioeconómico.
- Todos los datos de la solicitud técnica.
- La foto del paciente (si existe).
- El historial de estados de la silla.

---

### Módulo 7: Seguimiento de Armado de Silla

#### 4.7.1 Estados del Flujo

```
Registrada → En proceso de armado → Listo para entregar → Entregada
```

| Estado | Descripción | Color Badge |
|--------|-------------|-------------|
| `registrada` | El beneficiario fue registrado, la silla aún no se empieza a armar | Gris |
| `en_proceso` | Un técnico comenzó el armado de la silla | Amarillo |
| `lista` | La silla está armada y lista para ser entregada | Azul |
| `entregada` | La silla fue entregada al beneficiario | Verde |

#### 4.7.2 Cambio de Estado

- Solo los usuarios con rol **técnico** o **administrador** pueden cambiar el estado.
- El cambio es **secuencial** (no se puede saltar de "registrada" a "entregada").
- Al cambiar a `lista`, el técnico llena:
  - **Lugar de entrega**: Texto libre (ej: "León sede Forum").
  - **Fecha de entrega programada**: Date picker.

#### 4.7.3 Auditoría de Cambios

Cada cambio de estado se registra en una tabla `historial_estados` con:

| Campo | Descripción |
|-------|-------------|
| `id` | PK serial |
| `solicitud_id` | FK a `solicitudes_tecnicas` |
| `estado_anterior` | Estado previo |
| `estado_nuevo` | Estado al que se cambió |
| `usuario_id` | Quién hizo el cambio (técnico/admin) |
| `comentario` | Texto libre opcional |
| `created_at` | Timestamp del cambio |

#### 4.7.4 Notificaciones

Cuando el estado cambia a **`lista`** (listo para entregar), se dispara una notificación:

**Canal SMS/WhatsApp** (teléfono del Tutor 1 o Tutor 2):

> "¡Hola! Te informamos que la silla de ruedas para [NOMBRE_BENEFICIARIO] está lista para ser entregada. Será entregada en [LUGAR_ENTREGA] el día [FECHA_ENTREGA]. Agradecemos tu paciencia. — Ecosistema VIDA UG"

**Canal Email** (si hay correo registrado del tutor o beneficiario):

> Mismo mensaje, con formato HTML profesional y logos de la organización.

**Integración sugerida**:
- SMS: Twilio API o WhatsApp Business API.
- Email: Resend API (gratuito hasta 100 emails/día) o Supabase Edge Functions + SMTP.

---

## 5. Modelo de Datos (Supabase PostgreSQL)

### 5.1 Nuevas Tablas

```sql
-- Sistema de autenticación
CREATE TABLE usuarios (
    id              SERIAL PRIMARY KEY,
    nombre          TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    rol             TEXT NOT NULL CHECK(rol IN ('admin', 'capturista', 'tecnico')),
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Catálogo de regiones
CREATE TABLE paises (
    id          SERIAL PRIMARY KEY,
    nombre      TEXT NOT NULL UNIQUE,        -- "México", "USA", "Colombia"
    codigo      TEXT NOT NULL UNIQUE,         -- "MX", "US", "CO"
    activo      BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE regiones (
    id          SERIAL PRIMARY KEY,
    pais_id     INTEGER NOT NULL REFERENCES paises(id),
    nombre      TEXT NOT NULL,                -- "León, Gto", "Pearland, TX"
    codigo      TEXT NOT NULL,                -- "LON", "PRL" (3 letras)
    activo      BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(pais_id, codigo)
);

-- Contadores para generar folios secuenciales
CREATE TABLE region_counters (
    pais_codigo     TEXT NOT NULL,
    region_codigo   TEXT NOT NULL,
    anio            INTEGER NOT NULL,
    ultimo_numero   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (pais_codigo, region_codigo, anio)
);

-- Historial de estados de silla
CREATE TABLE historial_estados (
    id              SERIAL PRIMARY KEY,
    solicitud_id    INTEGER NOT NULL REFERENCES solicitudes_tecnicas(id) ON DELETE CASCADE,
    estado_anterior TEXT,
    estado_nuevo    TEXT NOT NULL,
    usuario_id      INTEGER NOT NULL REFERENCES usuarios(id),
    comentario      TEXT,
    lugar_entrega   TEXT,
    fecha_entrega   DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 5.2 Modificaciones a Tablas Existentes

```sql
-- beneficiarios: agregar folio, región y email
ALTER TABLE beneficiarios ADD COLUMN folio TEXT UNIQUE;
ALTER TABLE beneficiarios ADD COLUMN region_id INTEGER REFERENCES regiones(id);
ALTER TABLE beneficiarios ADD COLUMN sede TEXT;
ALTER TABLE beneficiarios ADD COLUMN email TEXT;

-- tutores: agregar email
ALTER TABLE tutores ADD COLUMN email TEXT;

-- solicitudes_tecnicas: agregar campo de estado de armado
ALTER TABLE solicitudes_tecnicas ADD COLUMN estado_silla TEXT NOT NULL DEFAULT 'registrada'
    CHECK(estado_silla IN ('registrada', 'en_proceso', 'lista', 'entregada'));
ALTER TABLE solicitudes_tecnicas ADD COLUMN lugar_entrega TEXT;
ALTER TABLE solicitudes_tecnicas ADD COLUMN fecha_entrega DATE;

-- capturistas: DEPRECADA — se reemplaza por tabla 'usuarios'
-- Los datos de capturistas se migran a 'usuarios' con rol='capturista'
```

### 5.3 Diagrama de Relaciones

```
usuarios ─┬── estudios_socioeconomicos (capturista_id → usuarios.id)
           ├── solicitudes_tecnicas    (capturista_id → usuarios.id)
           └── historial_estados       (usuario_id → usuarios.id)

paises ──── regiones ──── beneficiarios (region_id → regiones.id)

beneficiarios ─┬── tutores
               ├── estudios_socioeconomicos
               └── solicitudes_tecnicas ──── historial_estados
```

---

## 6. Pantallas y Navegación

### 6.1 Mapa de Navegación

```
Login
  │
  ├─ [Admin] ──→ Panel Admin
  │                 ├── Gestión de Usuarios (CRUD)
  │                 ├── Gestión de Regiones (CRUD)
  │                 ├── Panel de Registros (consulta + export)
  │                 └── Seguimiento de Sillas
  │
  ├─ [Capturista] ──→ Selección de Región/Sede
  │                       └── Estudio Socioeconómico
  │                             └── Solicitud Técnica
  │                                   └── Confirmación + Panel de Registros
  │
  └─ [Técnico] ──→ Panel de Seguimiento de Sillas
                       └── Cambio de Estado + Notificaciones
```

### 6.2 Archivos Frontend

| Archivo | Módulo | Descripción |
|---------|--------|-------------|
| `login.html` | Auth | Email + contraseña, redirección por rol |
| `seleccion-region.html` | Regiones | Selección de país, región y sede antes de registrar |
| `socioeconomico.html` | Registro | Formulario socioeconómico (actualizado con auto-fill) |
| `tecnica.html` | Registro | Solicitud técnica (actualizado con captura de foto) |
| `panel.html` | Consulta | Tabla de registros con filtros, búsqueda y exportación |
| `seguimiento.html` | Seguimiento | Panel para técnicos: cambio de estado de sillas |
| `admin-usuarios.html` | Admin | Alta, baja y edición de usuarios |
| `admin-regiones.html` | Admin | CRUD de países y regiones |

---

## 7. Endpoints de la API

### 7.1 Autenticación

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/auth/login` | Login con email + contraseña, retorna JWT |
| `POST` | `/api/auth/cambiar-password` | Cambio de contraseña |
| `GET` | `/api/auth/me` | Obtener datos del usuario logueado |

### 7.2 Usuarios (Admin)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/usuarios` | Listar todos los usuarios |
| `POST` | `/api/usuarios` | Crear nuevo usuario |
| `PATCH` | `/api/usuarios/{id}` | Editar usuario |
| `DELETE` | `/api/usuarios/{id}` | Desactivar usuario |

### 7.3 Regiones (Admin)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/paises` | Listar países activos |
| `POST` | `/api/paises` | Crear país |
| `GET` | `/api/regiones?pais_id=X` | Listar regiones por país |
| `POST` | `/api/regiones` | Crear región |
| `PATCH` | `/api/regiones/{id}` | Editar región |

### 7.4 Registros

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/estudios` | Crear estudio socioeconómico (genera folio) |
| `GET` | `/api/estudios/{id}` | Obtener estudio con datos completos |
| `PATCH` | `/api/estudios/{id}` | Actualizar borrador |
| `POST` | `/api/solicitudes` | Crear solicitud técnica |
| `GET` | `/api/solicitudes/{id}` | Obtener solicitud |
| `PATCH` | `/api/solicitudes/{id}` | Actualizar borrador |
| `POST` | `/api/upload-foto` | Subir foto a Supabase Storage |
| `GET` | `/api/beneficiarios/buscar?nombre=X&fecha_nacimiento=Y` | Validar duplicados |

### 7.5 Panel

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/panel/registros` | Listar registros con filtros (paginado) |
| `GET` | `/api/panel/registros/{folio}` | Detalle completo de un registro |
| `GET` | `/api/panel/exportar` | Generar datos para exportación a Excel |

### 7.6 Seguimiento de Sillas

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/seguimiento` | Listar solicitudes con estado de silla |
| `PATCH` | `/api/seguimiento/{solicitud_id}/estado` | Cambiar estado de silla |
| `GET` | `/api/seguimiento/{solicitud_id}/historial` | Ver historial de cambios |

### 7.7 Notificaciones

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/notificaciones/silla-lista` | Enviar notificación SMS/email |

---

## 8. Requerimientos No Funcionales

### 8.1 Rendimiento
- Soporte para **10+ capturistas concurrentes** de diferentes sedes.
- Paginación en el panel de registros (50 registros por página).
- Lazy loading de imágenes en vista de detalle.

### 8.2 Seguridad
- Contraseñas hasheadas con `bcrypt`.
- JWT con expiración de 8 horas (configurable).
- Middleware de autorización por rol en cada endpoint.
- Validación de archivos: SOLO `.jpg` y `.png`, max 10MB, en frontend Y backend.
- Sanitización de inputs para prevenir SQL injection (Pydantic + parameterized queries).

### 8.3 UX / Mobile-First
- Todos los formularios deben ser **completamente funcionales en smartphones**.
- La captura de foto debe usar la **cámara trasera por defecto** en dispositivos móviles.
- Los dropdowns de región y sede deben ser **buscables** (searchable select).
- Los cambios de estado deben tener **confirmación visual** (toast/snackbar).

### 8.4 Integridad de Datos
- Prevención de duplicados por nombre + fecha de nacimiento.
- Folios generados atómicamente (usar `SELECT FOR UPDATE` en contadores).
- Cascade delete limitado: solo tutores se eliminan con beneficiario. Estudios y solicitudes usan RESTRICT.
- La limpieza de la DB actual se hará con un script de migración que preserva la estructura pero elimina datos de prueba.

---

## 9. Bug Fixes Incluidos en v2

| ID | Bug | Solución |
|----|-----|----------|
| BUG-001 | Foto no se refleja en la DB al subir | Verificar endpoint `/api/upload-foto`, asegurar que retorna URL pública correcta y que se persiste en `foto_url` |
| BUG-002 | No hay opción de captura de foto en el momento | Implementar acceso a cámara con `getUserMedia()` API + botón "Tomar Foto" |

---

## 10. Plan de Migración

1. **Backup** de la DB actual (por precaución, aunque son datos de prueba).
2. **Script de limpieza**: `TRUNCATE` todas las tablas de datos, mantener estructura.
3. **Migraciones DDL**: Ejecutar las nuevas tablas y alteraciones listadas en la sección 5.
4. **Seed data**: Pre-cargar países iniciales (México, USA) y al menos 2 regiones por país.
5. **Crear usuario admin**: Seed con un usuario admin inicial para poder dar de alta al resto.
6. **Deprecar tabla `capturistas`**: Migrar lógica a tabla `usuarios` con `rol = 'capturista'`.

---

## 11. Fases de Implementación Sugeridas

### Fase 1: Fundación (Auth + Regiones + ID)
- Sistema de autenticación (login, JWT, roles).
- Gestión de usuarios (admin).
- Catálogo de regiones (CRUD admin, selección en flujo de registro).
- Generación de folio (ID estructurado).
- Limpieza de DB + migraciones.

### Fase 2: Formularios Mejorados
- Auto-llenado inteligente en formularios.
- Validación de duplicados de beneficiarios.
- Fix del bug de fotos + captura de foto en el momento.
- Nuevos campos (email beneficiario/tutor).

### Fase 3: Panel de Registros
- Tabla con filtros y búsqueda.
- Vista de detalle.
- Exportación a Excel.

### Fase 4: Seguimiento de Armado
- Panel de seguimiento para técnicos.
- Cambio de estado con auditoría.
- Sistema de notificaciones (SMS + Email).

---

## 12. Métricas de Éxito

| Métrica | Objetivo |
|---------|----------|
| Tiempo promedio de registro por beneficiario | Reducir de ~15 min a ~8 min |
| Registros duplicados | 0% (validación automática) |
| Trazabilidad de sillas | 100% de sillas con historial de estados |
| Notificaciones enviadas | 100% de beneficiarios notificados cuando la silla está lista |
| Capturistas concurrentes soportados | 10+ sin degradación |
