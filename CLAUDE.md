# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Sistema Integral de Gestión Social y Técnica** — a digital data collection system for a wheelchair donation program (Ecosistema VIDA UG). Replaces paper-based field registration with a mobile-first web app used by non-technical field workers ("capturistas") and technical staff.

The project is in **active implementation**. The `PRD.md` file at the repository root is the source of truth for requirements (an accurate, as-built PRD derived from the code and the live Supabase schema).

## Tech Stack

| Layer      | Technology                      | Notes                                                     |
| ---------- | ------------------------------- | --------------------------------------------------------- |
| Frontend   | HTML5, Tailwind CSS (CDN), Vanilla JS | Mobile-first; Fetch API with Bearer JWT auth        |
| Backend    | Python (FastAPI)                | RESTful API; JWT auth, role-based access                  |
| Database   | PostgreSQL via `psycopg2`       | Direct connection (`_DBAdapter` in `backend/database.py`); multi-region, atomic folio counters |
| Storage    | Supabase Storage (blobs only)   | Private buckets `fotos-tecnica` (technical exam images) and `documentos-estudio` (study docs); signed URLs |
| Auth       | JWT (HS256, 8h expiry)          | `python-jose` (`jose.jwt`) + `passlib[bcrypt]`           |

> **Note on Supabase**: Supabase is used **only** as the blob Storage backend for images/documents. The relational database is reached directly via `psycopg2` (`backend/database.py`), NOT through the Supabase client. The Supabase client (`create_client`) appears only in `backend/init_db.py` for bucket provisioning.

## Screens & Modules

| File                       | Role Access          | Purpose                                                    |
| -------------------------- | -------------------- | ---------------------------------------------------------- |
| `front/login.html`         | All                  | Email + password → JWT; routes by role                     |
| `front/seleccion-region.html` | capturista, tecnico | Select país/región + sede; saves `region_ctx` to localStorage |
| `front/socioeconomico.html`| capturista           | Beneficiary + guardian data + study; sends region_id + sede |
| `front/tecnica.html`       | tecnico              | Posture, measurements, photo upload, priority              |
| `front/admin-usuarios.html`| admin                | Create/list/deactivate system users                        |
| `front/admin-regiones.html`| admin                | Create/list países and regiones (folio catalog)            |

## Auth & Session Flow

```
login.html
  POST /api/auth/login {email, password}
  → localStorage['session'] = {token, nombre, rol, usuario_id}
  → admin        → admin-usuarios.html
  → capturista   → seleccion-region.html → socioeconomico.html
  → tecnico      → seleccion-region.html → tecnica.html
  → organizacion → seleccion-region.html → socioeconomico.html (captures on behalf of volunteers)

seleccion-region.html
  → localStorage['region_ctx'] = {pais_id, region_id, sede, nombres}
```

Every protected fetch MUST include: `Authorization: Bearer {session.token}`

## localStorage Keys

| Key           | Contents                                              | Cleared when      |
| ------------- | ----------------------------------------------------- | ----------------- |
| `session`     | `{token, nombre, rol, usuario_id}`                    | Logout            |
| `region_ctx`  | `{pais_id, region_id, sede, pais_nombre, region_nombre}` | Logout          |
| `estudio_id`  | Draft estudio ID for PATCH resumption                 | Study completed   |
| `beneficiario_id` | Links socioeconomico → tecnica                    | Tecnica completed |
| `solicitud_id`| Draft solicitud ID for PATCH resumption               | Solicitud completed |

## Backend Routers (`backend/routers/`)

All 9 routers are mounted under the `/api` prefix in `backend/main.py` (`include_router`).

| File                  | Auth Required                                   | Key Endpoints                                                                 |
| --------------------- | ----------------------------------------------- | ---------------------------------------------------------------------------- |
| `auth.py`             | —                                               | `POST /auth/login`, `GET /auth/me`                                            |
| `usuarios.py`         | admin                                           | `POST/GET /usuarios`, `PATCH /usuarios/{id}`, `DELETE /usuarios/{id}`         |
| `regiones.py`         | auth (reads) / admin (writes)                   | `GET /paises`, `PATCH /paises/{id}`, `GET /regiones`, `PATCH /regiones/{id}`  |
| `socioeconomico.py`   | capturista, organizacion, admin (+ tecnico on doc read) | `POST /estudios`, `GET/PATCH /estudios/{id}`, `POST /upload-documento`, `GET /me/capturas` |
| `tecnica.py`          | tecnico, admin (+ capturista, organizacion for shared reads/uploads) | `POST /solicitudes`, `GET /solicitudes/{id}`, `POST /upload-foto`, `POST /tecnica/procesos/{id}/finalizar` |
| `admin.py`            | admin                                           | `GET /admin/beneficiarios`, `GET /admin/beneficiarios/export`, `PATCH/DELETE /admin/beneficiarios/{id}` |
| `regiones.py`         | see above                                       | (folio catalog: países / regiones)                                           |
| `perfiles.py`         | auth / admin (per endpoint)                     | `GET/PATCH /me/perfil`, `GET /me/heatmap`, `GET/POST /organizaciones`, `POST /organizaciones/{id}/lider` |
| `finalizar.py`        | capturista, organizacion, admin                 | `POST /finalizar-registro`                                                    |
| `guardar_borrador.py` | capturista, organizacion, admin                 | `POST /guardar-borrador`, `GET /borrador/{estudio_id}`                        |

Role enforcement uses the `require_auth` / `require_admin` / `require_roles(...)` FastAPI dependencies defined in `backend/routers/auth.py`.

## Architecture Decisions

- **JWT auth**: HS256 tokens, 8h expiry (`JWT_EXPIRE_HOURS`, default 8). Secret from `JWT_SECRET` env var (must be ≥32 bytes; the dev placeholder is rejected at startup). Dependencies: `require_auth` / `require_admin` / `require_roles(...)` in `backend/routers/auth.py`.
- **Roles** (4): `admin`, `capturista`, `tecnico`, `organizacion`. Admin manages users and regions. Capturista does socioeconomic studies. Tecnico does technical exams. **Organizacion** accounts capture studies on behalf of volunteers who have NO system account — the volunteer's name is stored in `estudios.elaboro_estudio`, and `_upsert_voluntario` (`backend/routers/socioeconomico.py:738-741`) tracks their capture count. An org **leader** (via the `organizaciones_lideres` table) can see all studies captured under their organization through the `assert_resource_owner` leader bypass (`backend/routers/auth.py:163-196`).
- **Folio generation**: Atomic `INSERT ... ON CONFLICT DO UPDATE` on `region_counters`. Format: `{PAIS}-{REGION}-{YEAR}-{SEQ:03d}`. Generated server-side on POST /estudios.
- **Region context**: `region_id` and `sede` travel from `seleccion-region.html` via `localStorage['region_ctx']` into the POST /estudios body. NOT re-prompted per study.
- **Draft saving**: Both `/estudios` and `/solicitudes` support `status = 'borrador'`. IDs stored in localStorage for PATCH resumption.
- **Image upload**: `multipart/form-data` → backend validates MIME + extension (`.jpg`/`.png`) + size (≤ 10MB) → Supabase Storage → returns `foto_url`. Auth required.
- **Soft delete**: Users are deactivated (`activo = FALSE`), never hard-deleted.

## Database Schema (PostgreSQL)

> **Schema authority**: The authoritative schema lives in **Supabase (migrations + dashboard)** — the live `public` schema currently has ~16 tables. `backend/init_db.py` is a **legacy/incomplete bootstrap** (~10 tables, marked `LEGACY v1` at line 9); it does NOT define the full production schema and must not be treated as the source of truth. Tables such as `usuarios`, `paises`, `regiones`, and `region_counters` are FK-referenced by `init_db.py` but have no `CREATE TABLE` there — they exist only in the Supabase-managed schema. (Note: `init_db.py` *does* create the `organizaciones*` tables.)

The simplified shape below is a reading aid, not a DDL spec:

```
usuarios               (id, nombre, email, password_hash, rol, activo)
paises                 (id, nombre, codigo, activo)
regiones               (id, pais_id, nombre, codigo, activo)
region_counters        (pais_codigo, region_codigo, anio, ultimo_numero)  ← atomic folio counter
beneficiarios          (id, nombre, fecha_nacimiento, diagnostico, calle, colonia, ciudad,
                        telefonos, email, folio, region_id, sede)
tutores                (id, beneficiario_id, numero_tutor, nombre, edad, ...)
estudios_socioeconomicos (id, beneficiario_id, usuario_id, sede, status, ...)
solicitudes_tecnicas   (id, beneficiario_id, usuario_id, entorno, control_tronco,
                        peso_kg, foto_url, status, ...)
```

`tutores` supports 1–2 guardians per beneficiary (`numero_tutor` ∈ {1, 2}).

## Non-Functional Requirements

- **Mobile-first**: Fully functional on phones and tablets — field workers have no desktop access.
- **Responsiveness**: All forms must be usable on small screens (Tailwind responsive utilities required).
- **Numeric integrity**: Backend rejects malformed numeric inputs; frontend provides immediate client-side feedback.
- **Security**: JWT required on all non-login endpoints. Role enforcement in FastAPI dependencies, not just frontend redirects.

## Known Issues / Technical Debt

Tracked debt and audit findings live as GitHub issues in the repository. Base URL: `https://github.com/NeuxoraAI/Sillas-Rotary/issues`.

| Issue | Link |
| ----- | ---- |
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

Notable known debt confirmed during the code + DB audit:

- **Conflicting org-leadership source of truth** (#50–#61 range): `organizaciones.lider_usuario_id` (column) and the `organizaciones_lideres` (table) can disagree in live data. The `assert_resource_owner` bypass reads the **table**; any code reading the column is stale.
- **Tecnica leader bypass gap**: `tecnica.py` calls `assert_resource_owner` without `db`/`estudio_id` (lines ~1484, 1518, 1675), so org leaders are 403'd on `solicitudes técnicas` even when they can read the linked estudio.
- **Dead table `historial_estados`**: 0 rows, never wired into runtime.
- **Legacy `init_db.py`**: incomplete vs. the live Supabase schema (see Schema authority note above).
