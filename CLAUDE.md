# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Sistema Integral de Gestión Social y Técnica** — a digital data collection system for a wheelchair donation program (Ecosistema VIDA UG, developed by C-MED). Replaces paper-based field registration with a mobile-first web app used by non-technical field workers ("capturistas") and technical staff.

The project is in **active implementation** (Fase 7 Frontend complete). The `PRD.md` file is the source of truth for requirements.

## Tech Stack

| Layer      | Technology                      | Notes                                                     |
| ---------- | ------------------------------- | --------------------------------------------------------- |
| Frontend   | HTML5, Tailwind CSS (CDN), Vanilla JS | Mobile-first; Fetch API with Bearer JWT auth        |
| Backend    | Python (FastAPI)                | RESTful API; JWT auth, role-based access, Supabase glue   |
| Database   | PostgreSQL (via Supabase)       | Relational storage; multi-region, atomic folio counters   |
| Storage    | Supabase Storage                | Images (PNG/JPG) from technical exams (`fotos-tecnica`)   |
| Auth       | JWT (HS256, 8h expiry)          | `python-jose` + `passlib[bcrypt]`                         |

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

| File              | Prefix       | Auth Required      | Key Endpoints                          |
| ----------------- | ------------ | ------------------ | -------------------------------------- |
| `auth.py`         | `/api`       | —                  | `POST /auth/login`, `GET /auth/me`     |
| `usuarios.py`     | `/api`       | admin              | `POST/GET /usuarios`, `DELETE /usuarios/{id}` |
| `regiones.py`     | `/api`       | auth / admin       | `GET /paises`, `POST /paises`, `GET /regiones`, `POST /regiones` |
| `socioeconomico.py` | `/api`     | auth               | `POST /estudios`, `GET/PATCH /estudios/{id}` |
| `tecnica.py`      | `/api`       | auth               | `POST /solicitudes`, `GET/PATCH /solicitudes/{id}`, `POST /upload-foto` |

## Architecture Decisions

- **JWT auth**: HS256 tokens, 8h expiry. Secret from `JWT_SECRET` env var. `require_auth` / `require_admin` FastAPI dependencies.
- **Roles**: `admin`, `capturista`, `tecnico`. Admin manages users and regions. Capturista does socioeconomic studies. Tecnico does technical exams.
- **Folio generation**: Atomic `INSERT ... ON CONFLICT DO UPDATE` on `region_counters`. Format: `{PAIS}-{REGION}-{YEAR}-{SEQ:03d}`. Generated server-side on POST /estudios.
- **Region context**: `region_id` and `sede` travel from `seleccion-region.html` via `localStorage['region_ctx']` into the POST /estudios body. NOT re-prompted per study.
- **Draft saving**: Both `/estudios` and `/solicitudes` support `status = 'borrador'`. IDs stored in localStorage for PATCH resumption.
- **Image upload**: `multipart/form-data` → backend validates MIME + extension (`.jpg`/`.png`) + size (≤ 10MB) → Supabase Storage → returns `foto_url`. Auth required.
- **Soft delete**: Users are deactivated (`activo = FALSE`), never hard-deleted.

## Database Schema (PostgreSQL)

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
