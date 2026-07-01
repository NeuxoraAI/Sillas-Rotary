<!--
GitHub issue metadata — usar al crear el issue (gh issue create):

title:     fix(seguridad): técnico y admin tienen permisos de escritura sobre registros que contradicen el modelo de roles
labels:    seguridad, backend, type:bug, Alta
assignees: eramirezh10
state:     OPEN (propuesto)
-->

# fix(seguridad): técnico y admin tienen permisos de escritura sobre registros que contradicen el modelo de roles

| Campo | Valor |
| --- | --- |
| **Título** | `fix(seguridad): técnico y admin tienen permisos de escritura sobre registros que contradicen el modelo de roles` |
| **Labels** | `seguridad`, `backend`, `type:bug`, `Alta` |
| **Assignees** | `eramirezh10` |
| **Estado** | Propuesta (borrador) — pendiente de aprobación antes de implementar |

> Comando de referencia (no ejecutado):
> ```bash
> gh issue create \
>   --title "fix(seguridad): técnico y admin tienen permisos de escritura sobre registros que contradicen el modelo de roles" \
>   --label "seguridad,backend,type:bug,Alta" \
>   --assignee "eramirezh10" \
>   --body-file ISSUE_permisos_roles_escritura.md
> ```

## Pre-flight Checks
- [x] Searched existing issues for duplicates.
- [x] This issue must be approved before implementation work starts.

## Descripción del bug

El modelo de roles real de la aplicación, sobre **registros** (socioeconómico, técnica, gestión), es:

| Rol | Permisos sobre registros |
| --- | --- |
| `capturista` | **Crea** y llena registros; **edita** borradores |
| `organizacion` | Igual que capturista, capturando a nombre de voluntarios sin cuenta |
| `tecnico` | **Solo lectura**: ver / leer / descargar (Excel, fotos, PDF) |
| `admin` | **Ve, edita y elimina** registros ya guardados por el capturista — **NO crea** |

Regla de negocio confirmada: **solo el capturista (y la cuenta `organizacion`) crean registros.** Una vez que el capturista guardó un registro, el admin puede verlo, editarlo y eliminarlo, pero **nunca crearlo**. El técnico es estrictamente de lectura/descarga.

El backend **no** refleja este modelo: otorga permisos de **escritura** a `tecnico` y a `admin` en los endpoints de captura, cuando:

- `tecnico` no debe escribir nada (solo lectura).
- `admin` no debe **crear/capturar**; sus operaciones de edición y borrado ya tienen rutas dedicadas `/admin/beneficiarios/*`.

## Evidencia (auditoría de `require_roles`)

### Endpoints de ESCRITURA con roles incorrectos

| Endpoint | Ubicación | Roles actuales | Roles correctos |
| --- | --- | --- | --- |
| `POST /estudios` (crear) | `backend/routers/socioeconomico.py:645-649` | `capturista, admin, organizacion` | `capturista, organizacion` |
| `PATCH /estudios/{id}` (editar) | `backend/routers/socioeconomico.py:862-867` | `capturista, admin, organizacion` | `capturista, organizacion` |
| `POST /upload-documento` (subir doc) | `backend/routers/socioeconomico.py:587-591` | `capturista, admin, organizacion` | `capturista, organizacion` |
| `POST /solicitudes` (crear) | `backend/routers/tecnica.py:1388-1392` | `capturista, tecnico, admin, organizacion` | `capturista, organizacion` |
| `PATCH /solicitudes/{id}` (editar) | `backend/routers/tecnica.py:1507-1512` | `capturista, tecnico, admin, organizacion` | `capturista, organizacion` |
| `POST /upload-foto` (subir foto) | `backend/routers/tecnica.py:1351-1354` | `capturista, tecnico, admin, organizacion` | `capturista, organizacion` |
| `POST /guardar-borrador` | `backend/routers/guardar_borrador.py:509-513` | `capturista, admin, organizacion` | `capturista, organizacion` |
| `POST /finalizar-registro` | `backend/routers/finalizar.py:184-188` | `capturista, admin, organizacion` | `capturista, organizacion` |

> **Nota:** `tecnico` debe salir de **todos** los endpoints de escritura; `admin` debe salir de los endpoints de **captura/creación/edición general**. La edición y el borrado por parte del admin se canalizan por las rutas dedicadas (ver abajo), no por estos endpoints.

### Rutas dedicadas del admin (CORRECTAS — no cambiar)

El admin ya cuenta con sus propias rutas, restringidas a `require_roles("admin")`, para editar y eliminar registros existentes:

- `PATCH /admin/beneficiarios/{id}` — `backend/routers/admin.py:695-700`
- `PATCH /admin/beneficiarios/{id}/estudio` — `backend/routers/admin.py:731-736`
- `PATCH /admin/beneficiarios/{id}/solicitud` — `backend/routers/admin.py:765-770`
- `PATCH /admin/beneficiarios/{id}/gestion` — `backend/routers/admin.py:797-802`
- `DELETE /admin/beneficiarios/{id}` — `backend/routers/admin.py:871-875`

Estas rutas cubren el "editar y eliminar" del admin **sin** necesidad de que el admin esté en los endpoints de captura.

### Endpoints de LECTURA (CORRECTOS — no cambiar)

`tecnico` y/o `admin` aquí son acceso de lectura legítimo y deben permanecer:

- `GET /documentos` — `socioeconomico.py:625-628`
- `GET /estudios/{id}` — `socioeconomico.py:790-794`
- `GET /me/capturas` — `socioeconomico.py:825-828`
- `GET /borrador/{estudio_id}` — `guardar_borrador.py:943-947`
- `GET /solicitudes/{id}` — `tecnica.py:1479-1483`
- `GET /solicitudes/{id}/foto` — `tecnica.py:1670-1674`
- `GET /tecnica/beneficiarios`, `GET /tecnica/beneficiarios/export`, `GET /tecnica/beneficiarios/{id}` — `tecnica.py:854 / 965 / 1164`
- `GET /admin/beneficiarios`, `GET /admin/beneficiarios/export`, `GET /admin/beneficiarios/{id}` — `admin.py:437 / 509 / 675`

## Comportamiento esperado

- `tecnico` recibe **403** al crear/editar registros o subir fotos/documentos; conserva intacto todo su acceso de lectura/descarga.
- `admin` recibe **403** en los endpoints de **captura** (`POST /estudios`, `POST /solicitudes`, `POST /upload-foto`, `POST /upload-documento`, `POST /guardar-borrador`, `POST /finalizar-registro`, `PATCH /estudios/{id}`, `PATCH /solicitudes/{id}`); el admin edita/elimina **únicamente** vía rutas `/admin/beneficiarios/*`.
- `capturista` y `organizacion` conservan su acceso de captura/edición de borradores.

## Comportamiento actual

- Un `tecnico` puede crear (`POST /solicitudes`), editar (`PATCH /solicitudes/{id}`) y subir fotos (`POST /upload-foto`).
- Un `admin` puede crear y capturar registros (`POST /estudios`, `POST /solicitudes`, `POST /finalizar-registro`, etc.), contradiciendo "el admin no crea, solo ve/edita/elimina lo ya guardado".

## Solución sugerida

1. **Backend** — ajustar los `require_roles(...)` de los 8 endpoints de escritura listados a `("capturista", "organizacion")`.
2. **Frontend** — verificar que la UI técnica (`front/tecnica.html`) quede en solo lectura (alinear con #97) y que la UI admin use exclusivamente las rutas `/admin/beneficiarios/*` para editar/eliminar.
3. **Tests de regresión** por rol para cada endpoint afectado:
   - `tecnico` → 403 en create/patch/upload.
   - `admin` → 403 en los endpoints de captura; → 200 en sus rutas `/admin/*`.
   - `capturista` / `organizacion` → 200/201 (sin cambios).

## Relación con otros issues

- **#97** (eliminar proceso técnico/manufactura): complementario; deja al técnico en solo lectura del **proceso**, pero **no** toca los permisos de `solicitudes_tecnicas`. Este issue cierra ese flanco.
- **#109** (bypass de líder en `finalizar`): independiente. #109 corrige el argumento `db`/`estudio_id` en `assert_resource_owner` (línea ~219); este issue ajusta la lista de roles del decorador (línea ~188). No hay conflicto, pero ambos tocan `finalizar.py`.
- **Deuda conocida** (`admin-solicitud-write-gap`): al canalizar la edición del admin por `/admin/beneficiarios/{id}/solicitud`, recordar que hoy ese PATCH puede dar 404 cuando no existe solicitud previa. No se resuelve en este issue, pero conviene tenerlo presente al validar el flujo de edición del admin.

## Criterios de aceptación

- [ ] `tecnico` recibe 403 en `POST /estudios`, `PATCH /estudios/{id}`, `POST /upload-documento`, `POST /solicitudes`, `PATCH /solicitudes/{id}`, `POST /upload-foto`, `POST /guardar-borrador`, `POST /finalizar-registro`.
- [ ] `admin` recibe 403 en esos mismos endpoints de captura.
- [ ] `admin` conserva 200 en `PATCH /admin/beneficiarios/*` y `DELETE /admin/beneficiarios/{id}`.
- [ ] `tecnico` y `admin` conservan 200 en todos los endpoints de lectura/descarga.
- [ ] `capturista` y `organizacion` conservan su acceso actual de escritura.
- [ ] Tests de regresión por rol para cada endpoint afectado.
