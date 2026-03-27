# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Sistema Integral de Gestión Social y Técnica** — a digital data collection system for a wheelchair donation program (Ecosistema VIDA UG, developed by C-MED). Replaces paper-based field registration with a mobile-first web app used by non-technical field workers ("capturistas").

The project is currently in **pre-implementation phase**. Only `PRD.md` exists as the source of truth. All architecture and screen decisions should align with it.

## Tech Stack

| Layer      | Technology                      | Notes                                       |
| ---------- | ------------------------------- | ------------------------------------------- |
| Frontend   | HTML5, Tailwind CSS, Vanilla JS | Mobile-first; Fetch API to backend          |
| Backend    | Python (FastAPI or Flask)       | RESTful API; business logic + Supabase glue |
| Database   | Supabase (PostgreSQL)           | Relational storage for all form data        |
| Storage    | Supabase Storage                | Images (PNG/JPG) from technical exams       |

## Screens & Modules

| File               | Module                     | Purpose                                      |
| ------------------ | -------------------------- | -------------------------------------------- |
| `Login_Andre.html` | Module 1 – Access          | Capturista name capture; no password         |
| `code (1).html`    | Module 2 – Socioeconomic   | Beneficiary + guardian data + study closure  |
| `code.html`        | Module 3 – Technical Exam  | Posture, measurements, photo upload, priority |

## Architecture Decisions (from PRD)

- **Session identity**: Backend generates a temporary token or `localStorage` ID tied to the capturista name — no full auth system.
- **Draft saving**: Socioeconomic study supports "borrador" state stored locally or in DB with `status = 'incompleto'`.
- **Image upload flow**: Frontend sends file via `multipart/form-data` → Python backend validates extension + size → uploads to Supabase Storage bucket → returns public/signed URL saved in `solicitudes_tecnicas.foto_url`.
- **File security**: Accept only `.jpg` / `.png` on both frontend (`accept` attribute) and backend (MIME + extension check). This is a hard requirement.
- **Backend validation**: All numeric fields (measurements in inches, weight, age, monthly income) must be validated server-side before Supabase insertion.

## Database Schema (Supabase PostgreSQL)

```
capturistas            (id, nombre, fecha_registro)
beneficiarios          (id, nombre, fecha_nacimiento, diagnostico, domicilio, ...)
tutores                (id, beneficiario_id, nombre, ingreso, empleo, ...)
estudios_socioeconomicos (id, beneficiario_id, capturista_id, fecha, sede, ...)
solicitudes_tecnicas   (id, beneficiario_id, capturista_id, entorno,
                        control_tronco, peso, foto_url, ...)
```

`tutores` supports 1–2 guardians per beneficiary (linked via `beneficiario_id`).

## Non-Functional Requirements

- **Mobile-first**: Fully functional on phones and tablets — field workers have no desktop access.
- **Responsiveness**: All forms must be usable on small screens (Tailwind responsive utilities required).
- **Numeric integrity**: Backend rejects malformed numeric inputs; frontend provides immediate client-side feedback.
