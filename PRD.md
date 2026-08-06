# PRD — Sistema Integral de Gestión Social y Técnica (SIG-Tec)

**Producto**: SIG-Tec, sistema digital de captura de datos para un programa de donación de sillas de ruedas (Ecosistema VIDA UG).
**Estado**: Implementación activa.
**Naturaleza de este documento**: PRD *as-built* (tal como está construido). Cada afirmación factual se rastrea a un archivo fuente con rango de líneas o a un hecho verificado del esquema en vivo de Supabase. No contiene afirmaciones inventadas.

> Las etiquetas `archivo:líneas` indican la evidencia en el código fuente. Los identificadores de código, rutas y nombres de tablas se conservan tal cual.

---

## 1. Overview (Visión general)

El sistema reemplaza el registro de campo en papel por una aplicación web *mobile-first* utilizada por personal de campo no técnico (capturistas), personal técnico (técnicos) y organizaciones aliadas. El frontend (`front/*.html`) consume una API REST de FastAPI mediante `fetch` con autenticación `Bearer` JWT.

Tipos de usuario:

- **Beneficiario**: la persona registrada que recibe la silla de ruedas. No tiene cuenta en el sistema.
- **Capturista**: levanta los estudios socioeconómicos en campo.
- **Técnico**: realiza el examen técnico (postura, mediciones, foto, prioridad).
- **Organización** (`rol = 'organizacion'`): cuenta que captura estudios **en nombre de voluntarios** que NO tienen cuenta propia en el sistema.
- **Voluntario**: persona que recolecta datos bajo una organización; NO tiene login. Su nombre se guarda en `estudios.elaboro_estudio`.
- **Admin**: administra usuarios, regiones/países y catálogos.

Fuente: `backend/main.py` (montaje de la app y routers), `backend/routers/auth.py` (modelo de roles).

---

## 2. Roles & Auth (Roles y autenticación)

### 2.1 Autenticación

- Esquema **JWT HS256**, expiración de **8 horas** (`JWT_EXPIRE_HOURS`, default `8`). — `backend/routers/auth.py:41-42, 80-83`
- El secreto proviene de la variable de entorno `JWT_SECRET`; debe medir ≥32 bytes y el placeholder de desarrollo se rechaza en el arranque. — `backend/routers/auth.py:32-40`
- Librerías: `python-jose` (`jose.jwt`) para tokens y `passlib[bcrypt]` para el hash de contraseñas. — `backend/routers/auth.py:18-19, 86-94`
- Endpoints de sesión: `POST /api/auth/login` y `GET /api/auth/me`. — `backend/routers/auth.py:210, 244`

### 2.2 Roles (4)

Exactamente **cuatro** roles, leídos desde `usuarios.rol` en `require_auth`: `admin`, `capturista`, `tecnico`, `organizacion`. — `backend/routers/auth.py:101-133`

| Rol            | Alcance de acceso |
| -------------- | ----------------- |
| `admin`        | Acceso total: usuarios, países/regiones, beneficiarios; bypass de propiedad de recursos. |
| `capturista`   | Crea/edita estudios socioeconómicos; borradores; finalización de registro. |
| `tecnico`      | Realiza solicitudes técnicas, procesos técnicos y subida de fotos. |
| `organizacion` | Captura estudios en nombre de voluntarios; un líder de organización ve los estudios de su organización. |

### 2.3 Dependencias de autorización

Definidas en `backend/routers/auth.py`:

- `require_auth` — valida el JWT y devuelve el usuario actual. — `auth.py:101-133`
- `require_admin` — exige rol `admin` (403 en caso contrario). — `auth.py:136-145`
- `require_roles(*roles)` — fábrica de dependencias que permite solo los roles indicados. — `auth.py:148-160`
- `assert_resource_owner(...)` — permite acceso a admin, exige propiedad por `usuario_id`, o aplica el **bypass de líder de organización**: si `db` y `estudio_id` se proporcionan, consulta `organizaciones` ⋈ `organizaciones_lideres` para autorizar al líder de la organización dueña del estudio. — `auth.py:163-196`

---

## 3. Data Layer (Capa de datos)

- **Base de datos**: PostgreSQL accedido **directamente vía `psycopg2`** mediante el adaptador `_DBAdapter`. NO se usa el cliente de Supabase para la base relacional. — `backend/database.py:6-7, 94-158`
- **Almacenamiento de blobs**: **Supabase Storage**, usado únicamente para imágenes y documentos. El cliente de Supabase (`create_client`) aparece solo en `backend/init_db.py` para provisionar buckets. — `backend/init_db.py:1-4, 240-274`
- **Buckets** (ambos privados, límite de 10 MB): `fotos-tecnica` (imágenes de examen técnico, MIME `image/jpeg`, `image/png`) y `documentos-estudio` (documentos de estudio, MIME `image/jpeg`, `image/png`, `application/pdf`). — `backend/init_db.py:245-261`
- **Autoridad del esquema**: el esquema autoritativo vive en **Supabase (migraciones + dashboard)** — el esquema `public` en vivo tiene ~16 tablas. `backend/init_db.py` es un **bootstrap legado/incompleto** (~10 tablas, marcado `LEGACY v1` en la línea 9) y NO debe tratarse como fuente de verdad del esquema. — `backend/init_db.py:7-13`; auditoría del esquema en vivo de Supabase (hecho verificado).

---

## 4. Routers / API Surface (Superficie de API)

Los **9 routers** se montan bajo el prefijo `/api` en `backend/main.py`. — `backend/main.py:12, 63-71`

| Router                | Roles requeridos (evidencia)                                            | Endpoints clave |
| --------------------- | ----------------------------------------------------------------------- | --------------- |
| `auth.py`             | público (login) / autenticado (`/me`)                                   | `POST /auth/login`, `GET /auth/me` — `auth.py:210, 244` |
| `usuarios.py`         | `admin` — `usuarios.py:117, 175, 206, 315`                              | `POST/GET /usuarios`, `PATCH /usuarios/{id}`, `DELETE /usuarios/{id}` |
| `regiones.py`         | `require_auth` (lecturas) / `admin` (escrituras) — `regiones.py:222, 254, 389, 437` | `GET /paises`, `PATCH /paises/{id}`, `GET /regiones`, `PATCH /regiones/{id}` |
| `socioeconomico.py`   | `capturista`, `admin`, `organizacion` (+ `tecnico` en lectura de documentos) — `socioeconomico.py:591, 628, 649, 794, 867` | `POST /estudios`, `GET/PATCH /estudios/{id}`, `POST /upload-documento`, `GET /me/capturas` |
| `tecnica.py`          | `tecnico`, `admin` (+ `capturista`, `organizacion` en lecturas/subidas compartidas) — `tecnica.py:1179, 1348, 1386, 1475` | `POST /solicitudes`, `GET /solicitudes/{id}`, `POST /upload-foto`, `POST /tecnica/procesos/{id}/finalizar` |
| `perfiles.py`         | `require_auth` / `admin` según endpoint — `perfiles.py:189, 464, 540, 692` | `GET/PATCH /me/perfil`, `GET /me/heatmap`, `GET/POST /organizaciones`, `POST /organizaciones/{id}/lider` |
| `finalizar.py`        | `capturista`, `admin`, `organizacion` — `finalizar.py:188`             | `POST /finalizar-registro` |
| `guardar_borrador.py` | `capturista`, `admin`, `organizacion` — `guardar_borrador.py:513, 954` | `POST /guardar-borrador`, `GET /borrador/{estudio_id}` |
| `admin.py`            | `admin` — `admin.py:440, 512, 679, 893`                                | `GET /admin/beneficiarios`, `GET /admin/beneficiarios/export`, `PATCH/DELETE /admin/beneficiarios/{id}` |

---

## 5. Org Capture Model (Modelo de captura por organización)

- Las cuentas de organización (`rol = 'organizacion'`) **inician sesión** y capturan estudios. — `backend/routers/auth.py:101-133`
- Los **voluntarios NO tienen cuenta** en el sistema. El nombre del voluntario se guarda como texto en `estudios.elaboro_estudio`. — `backend/routers/socioeconomico.py:726, 739`
- Al crear un estudio con rol `organizacion`, se ejecuta `_upsert_voluntario`, que localiza la organización (`organizaciones.usuario_id = usuario_id`) e incrementa `organizaciones_voluntarios.capturas_count` (con `ON CONFLICT DO UPDATE`). — `backend/routers/socioeconomico.py:738-741, 752-790`
- El vínculo estudio → organización es `estudios.usuario_id = organizaciones.usuario_id`. — `backend/routers/socioeconomico.py:760-766`
- Un **líder** de organización (registrado en la tabla `organizaciones_lideres`) puede ver todos los estudios capturados bajo su organización a través del bypass de `assert_resource_owner`. — `backend/routers/auth.py:179-191`

---

## 6. Core Flows (Flujos principales)

### 6.1 Login y enrutamiento por rol

`POST /api/auth/login` devuelve `{access_token, rol, nombre, usuario_id}`; el frontend guarda `localStorage['session']` y enruta por rol. — `backend/routers/auth.py:210-242`; `front/login.html`.

### 6.2 Contexto de región

`front/seleccion-region.html` guarda `localStorage['region_ctx']` con `{pais_id, region_id, sede, ...}`, que viaja en el cuerpo de `POST /estudios` y no se vuelve a pedir por estudio.

### 6.3 Generación de folio (atómica)

`generate_folio(db, region_id)` usa un único `INSERT ... ON CONFLICT (pais_codigo, region_codigo, anio) DO UPDATE SET ultimo_numero = region_counters.ultimo_numero + 1` sobre `region_counters` para asignar de forma atómica el número secuencial. — `backend/routers/regiones.py:127-178`

El formato del folio es `{PAIS}-{REGION}-{AÑO}-{NUM:03d}` (ej. `MX-LON-2026-001`), con el número rellenado a un mínimo de 3 dígitos. — `backend/utils/folio.py` (`format_folio`).

### 6.4 Borrador → finalización

El estudio se puede guardar como borrador (`POST /guardar-borrador`, router `guardar_borrador.py`) y luego completarse con `POST /finalizar-registro` (router `finalizar.py`). — `backend/routers/guardar_borrador.py:509`, `backend/routers/finalizar.py:184`

### 6.5 Examen técnico

El técnico levanta la solicitud técnica (`POST /solicitudes`), sube la foto (`POST /upload-foto`) y gestiona el proceso técnico (`/tecnica/procesos/{id}/...`). — `backend/routers/tecnica.py:1345, 1382, 1242`

### 6.6 Resaltado de campos faltantes al redirigir entre formularios (Issue #123)

Cuando una validación (local o del servidor en `POST /finalizar-registro`) detecta
campos obligatorios/ inválidos, el modal de validación ofrece **"Ir al formulario"**.
Al pulsarlo, los errores se transfieren entre páginas para resaltar los campos en
el destino, reutilizando `SR_Validations.showFieldError`. — `front/assets/js/validations.js`.

- **Fuente de verdad del mapeo**: `SR_Validations.resolveFieldTarget(form, field)` traduce
  el par backend `{form, field}` (p. ej. `finalizar.py` emite `credencial_url`, `curp_benef`,
  `imss_estatus`) al objetivo del frontend `{page, name | container/legend}`. Los nombres del
  backend **no** coinciden con los `name` de los inputs (`curp_benef→curp`,
  `tuvo_silla_previa→silla_previa`, `imss_estatus→tutor1_imss`); las evidencias `*_url`
  (`credencial_url`, `comprobante_domicilio_url`, `foto_url`) se resaltan por zona de subida
  + leyenda. El caso cross-form `beneficiario/diagnostico` se enruta a `tecnica.html` (donde
  vive el input). El flujo de finalización (`gestion.html`) deriva **la URL del botón y el
  resaltado** de esta misma función, evitando enrutar el stash a una página distinta de la
  navegada.
- **Persistencia**: `stashFieldErrors` / `persistStashEntries` guardan las entradas ya
  resueltas en `sessionStorage['sr_pending_field_errors']`, agrupadas por página destino.
- **Consumo**: al cargar el destino, `applyStashedFieldErrors(page)` lee **y borra** la clave
  (consumo único), aplica el resaltado (`showFieldError` / `showEvidenceError`), y hace
  `scrollIntoView` + `focus()` al primer campo pendiente. Los resaltados de texto se limpian al
  escribir; los de evidencia, al adjuntar archivo. La clave se limpia también en logout /
  nueva captura (`perfil-capturista.html` `_clearDraftStorage`).

> **Nota operativa**: `validations.js` es un asset estático servido por FastAPI (`StaticFiles`,
> sin `Cache-Control` de larga duración). Tras actualizarlo, forzar recarga (Ctrl/Cmd+Shift+R)
> o purgar la caché del CDN si el comportamiento no aparece; los handlers registran un
> `console.warn` cuando `SR_Validations.persistStashEntries` no está disponible (síntoma de un
> `validations.js` cacheado).

---

## 7. Database Schema (Resumen del esquema)

> **Autoridad**: el esquema autoritativo es **Supabase (migraciones + dashboard)**, ~16 tablas en producción. `backend/init_db.py` es legado/incompleto (~10 tablas) y NO refleja la totalidad del esquema en vivo. — `backend/init_db.py:7-13`; auditoría de Supabase (hecho verificado).

Tablas clave (forma simplificada, no es una especificación DDL):

```
usuarios                   (id, nombre, email, password_hash, rol, activo)
paises                     (id, nombre, codigo, activo)
regiones                   (id, pais_id, nombre, codigo, activo)
region_counters            (pais_codigo, region_codigo, anio, ultimo_numero)  ← contador de folio atómico
beneficiarios              (id, nombre, fecha_nacimiento, diagnostico, ..., folio, region_id, sede)
tutores                    (id, beneficiario_id, numero_tutor ∈ {1,2}, nombre, edad, ...)
estudios (socioeconómicos) (id, beneficiario_id, usuario_id, elaboro_estudio, sede, status, ...)
solicitudes_tecnicas       (id, beneficiario_id, usuario_id, entorno, control_tronco, peso_kg, foto_url, status, ...)
```

Tablas referenciadas por FK en `init_db.py` pero **sin `CREATE TABLE` ahí** (existen solo en el esquema gestionado por Supabase): `usuarios`, `paises`, `regiones`, `region_counters`. En cambio, `init_db.py` **sí** crea las tablas `organizaciones`, `organizaciones_lideres`, `organizaciones_miembros` y `organizaciones_voluntarios` (`backend/init_db.py:165, 183, 191, 200`).

---

## 8. Non-Functional Requirements (Requisitos no funcionales)

- **Mobile-first**: la aplicación debe ser plenamente funcional en teléfonos y tablets; el personal de campo no tiene acceso a escritorio.
- **Seguridad**: JWT obligatorio en todos los endpoints que no sean de login; la aplicación de roles ocurre en dependencias de FastAPI, no solo en redirecciones del frontend. — `backend/routers/auth.py:101-160`
- **Integridad numérica**: el backend rechaza entradas numéricas malformadas; el frontend ofrece retroalimentación inmediata del lado del cliente.
- **Cabeceras de seguridad**: middleware aplica `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy` y `Cache-Control: no-store` en rutas `/api/`. — `backend/main.py:18-22, 36-61`

---

## 9. Known Issues / Technical Debt (Deuda técnica conocida)

La deuda y los hallazgos de auditoría se rastrean como issues de GitHub. URL base: `https://github.com/NeuxoraAI/Sillas-Rotary/issues`.

| Issue | Enlace |
| ----- | ------ |
| #50 | https://github.com/NeuxoraAI/Sillas-Rotary/issues/50 |
| #51 | https://github.com/NeuxoraAI/Sillas-Rotary/issues/51 |
| #52 | https://github.com/NeuxoraAI/Sillas-Rotary/issues/52 |
| #53 | https://github.com/NeuxoraAI/Sillas-Rotary/issues/53 |
| #54 | https://github.com/NeuxoraAI/Sillas-Rotary/issues/54 |
| #55 | https://github.com/NeuxoraAI/Sillas-Rotary/issues/55 |
| #56 | https://github.com/NeuxoraAI/Sillas-Rotary/issues/56 |
| #57 | https://github.com/NeuxoraAI/Sillas-Rotary/issues/57 |
| #58 | https://github.com/NeuxoraAI/Sillas-Rotary/issues/58 |
| #59 | https://github.com/NeuxoraAI/Sillas-Rotary/issues/59 |
| #60 | https://github.com/NeuxoraAI/Sillas-Rotary/issues/60 |
| #61 | https://github.com/NeuxoraAI/Sillas-Rotary/issues/61 |

Deuda notable confirmada durante la auditoría de código + base de datos:

- **Fuente de verdad de liderazgo de organización en conflicto**: la columna `organizaciones.lider_usuario_id` y la tabla `organizaciones_lideres` pueden discrepar en datos en vivo. El bypass de `assert_resource_owner` lee la **tabla**; cualquier código que lea la columna queda obsoleto. — `backend/routers/auth.py:179-191`
- **Brecha del bypass de líder en `tecnica.py`**: `tecnica.py` invoca `assert_resource_owner` sin `db`/`estudio_id` (líneas ~1484, 1518, 1675), por lo que los líderes de organización reciben 403 en solicitudes técnicas aun cuando pueden leer el estudio vinculado.
- **Schema legacy limpiado**: `historial_estados`, `capturistas` y `capturista_id` quedaron programados para eliminación mediante migración incremental.
- **`init_db.py` legado**: incompleto frente al esquema en vivo de Supabase (ver la nota de autoridad del esquema en la sección 3).
