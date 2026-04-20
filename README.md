<div align="center">

<img src="front/assets/Logo_ug.png" height="80" alt="Universidad de Guanajuato"/>
&nbsp;&nbsp;&nbsp;&nbsp;
<img src="front/assets/Logo_rotary_200.png" height="80" alt="Rotary 200"/>
&nbsp;&nbsp;&nbsp;&nbsp;
<img src="front/assets/logo_vida_ug.png" height="80" alt="Ecosistema VIDA UG"/>

<br/><br/>

# Sistema Integral de Gestión Social y Técnica
## Ecosistema VIDA UG

> Digitalización del programa de donación de sillas de ruedas — eliminando el papel en el trabajo de campo.

<br/>

[![Estado](https://img.shields.io/badge/Estado-Operativo-brightgreen?style=for-the-badge)](https://github.com/AndreRaz/Sillas-Rotary)
[![Python](https://img.shields.io/badge/Python-3.12-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Tailwind](https://img.shields.io/badge/Tailwind_CSS-CDN-38bdf8?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://supabase.com)

</div>

---

## Índice

- [¿Qué es este sistema?](#qué-es-este-sistema)
- [Capturas de pantalla](#capturas-de-pantalla)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Requisitos previos](#requisitos-previos)
- [Instalación y puesta en marcha](#instalación-y-puesta-en-marcha)
- [Cómo funciona la aplicación](#cómo-funciona-la-aplicación)
- [Módulos del sistema](#módulos-del-sistema)
- [API — Endpoints](#api--endpoints)
- [Base de datos](#base-de-datos)
- [Ver los datos registrados](#ver-los-datos-registrados)
- [Seguridad](#seguridad)
- [Roadmap a producción](#roadmap-a-producción)
- [Desarrollado por NEUXORA](#desarrollado-por-neuxora)

---

## ¿Qué es este sistema?

El **Sistema Integral de Gestión Social y Técnica** es una aplicación web **mobile-first** diseñada para capturistas de campo del programa **Ecosistema VIDA UG** (Universidad de Guanajuato + Rotary 200).

### El problema que resuelve

Antes del sistema, el proceso era completamente en papel:
los capturistas llenaban formularios físicos en campo, los datos se transcribían manualmente, se perdía información, y no existía trazabilidad de los expedientes.

### La solución

Una app web que funciona en cualquier teléfono o tablet, sin instalación, sin contraseña compleja. El capturista registra su nombre y puede capturar expediente tras expediente en el mismo turno.

### ¿Qué registra?

| Módulo | Datos capturados |
|---|---|
| **Acceso** | Email + contraseña → JWT (roles: admin, capturista, tecnico) |
| **Estudio socioeconómico** | Datos del beneficiario, domicilio, tutores, ingresos familiares, historial |
| **Solicitud técnica** | Entorno de uso, capacidad postural, 5 medidas corporales en pulgadas, fotografía clínica, prioridad |

---

## Estructura del proyecto

```
Sillas-Rotary/
│
├── front/                          # Frontend — HTML5 + Tailwind CSS + Vanilla JS
│   ├── login.html                  # Módulo 1 — Acceso al sistema
│   ├── socioeconomico.html         # Módulo 2 — Estudio socioeconómico
│   ├── tecnica.html                # Módulo 3 — Solicitud técnica + medidas + foto
│   └── assets/                     # Recursos estáticos locales
│       ├── Logo_ug.png             # Logo Universidad de Guanajuato
│       ├── Logo_rotary_200.png     # Logo Rotary 200
│       ├── logo_vida_ug.png        # Logo Ecosistema VIDA UG
│       ├── guia_clinica.png        # Diagrama de referencia — toma de medidas
│       └── iconografia_silla.png   # Ícono de silla de ruedas
│
├── backend/                        # API REST — FastAPI + Supabase/PostgreSQL
│   ├── main.py                     # Punto de entrada: CORS, rutas, static files, security headers
│   ├── database.py                 # Conexión PostgreSQL + test guardrails
│   ├── init_db.py                  # DDL: crea tablas e índices al iniciar
│   ├── migrations/                 # Migraciones SQL incrementales
│   ├── requirements.txt            # Dependencias Python
│   ├── start.sh                    # Script de arranque (crea venv + levanta servidor)
│   ├── .env.example                # Plantilla de variables de entorno
│   └── routers/
│       ├── auth.py                 # POST /api/auth/login (JWT HS256)
│       ├── socioeconomico.py       # Estudio socioeconómico (crear, actualizar, obtener)
│       ├── tecnica.py              # Solicitud técnica + upload de foto + signed URL
│       ├── usuarios.py             # CRUD de usuarios (admin)
│       └── regiones.py             # CRUD de países y regiones (admin)
│
├── PRD.md                          # Product Requirements Document original
├── .gitignore
└── README.md
```

---

## Requisitos previos

| Herramienta | Versión mínima | Notas |
|---|---|---|
| **Python** | 3.12 | `pydantic-core` no soporta Python 3.14 todavía |
| **Navegador** | Cualquier moderno | Chrome, Firefox, Safari — desktop y mobile |
| **Node.js** | — | **No requerido** — Tailwind CSS se carga vía CDN |
| **Git** | Cualquier | Para clonar el repositorio |

---

## Instalación y puesta en marcha

### 1. Clonar el repositorio

```bash
git clone https://github.com/AndreRaz/Sillas-Rotary.git
cd Sillas-Rotary
```

### 2. Levantar el backend

```bash
cd backend
bash start.sh
```

El script hace todo automáticamente:

```
→ Crea el entorno virtual con Python 3.12
→ Instala las dependencias de requirements.txt
→ Inicializa la base de datos (tablas + índices via init_db.py)
→ Levanta el servidor en http://localhost:8000
```

Para verificar que está corriendo:

```bash
curl http://localhost:8000/
# {"status":"ok","sistema":"Sillas Rotary API"}
```

> **Nota:** La documentación interactiva de la API (`/docs`, `/redoc`) se desactiva automáticamente en producción (`ENV=production`).

### 3. Abrir el frontend

Abrir `front/login.html` directamente en el navegador (doble click o drag & drop).

> **Nota:** Los HTMLs usan rutas relativas entre sí (`login.html` → `socioeconomico.html` → `tecnica.html`) y hacia `assets/`, por lo que funcionan perfectamente abriendo los archivos con `file://` sin necesidad de un servidor adicional.

### Dependencias Python

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
python-multipart==0.0.9
aiofiles==23.2.1
pydantic==2.7.4
psycopg2-binary        # PostgreSQL driver
supabase               # Supabase client (storage, auth)
python-jose[cryptography]  # JWT
passlib[bcrypt]        # Password hashing
```

---

## Cómo funciona la aplicación

```
┌──────────────────────────────────────────────────────┐
│                    login.html                        │
│                                                      │
│  El usuario ingresa email + contraseña               │
│  POST /api/auth/login → JWT en localStorage          │
│  Si ya hay sesión → redirige según rol               │
│    admin     → admin-usuarios.html                   │
│    capturista→ seleccion-region → socioeconomico     │
│    tecnico   → seleccion-region → tecnica            │
└─────────────────────┬────────────────────────────────┘
                       │  ✓ sesión activa (JWT)
                       ▼
┌──────────────────────────────────────────────────────┐
│               socioeconomico.html                    │
│                                                      │
│  Datos del beneficiario + 1 o 2 tutores              │
│  POST /api/estudios → Authorization: Bearer <token>  │
│  Permite guardar borrador o estudio completo         │
└─────────────────────┬────────────────────────────────┘
                       │  ✓ estudio guardado
                       ▼
┌──────────────────────────────────────────────────────┐
│                  tecnica.html                        │
│                                                      │
│  Entorno, capacidad postural, medidas, foto          │
│  POST /api/upload-foto (opcional)                    │
│  POST /api/solicitudes                               │
│                                                      │
│  Al guardar completo → limpia beneficiario_id        │
└─────────────────────┬────────────────────────────────┘
                       │  ✓ solicitud guardada
                       ▼
              socioeconomico.html
           (mismo capturista, nuevo beneficiario)
```

---

## Módulos del sistema

### Módulo 1 — Acceso (`login.html`)

- El usuario ingresa email y contraseña (JWT HS256, 8h expiración)
- El backend valida contra la tabla `usuarios` y retorna un token JWT
- La sesión se guarda en `localStorage` con `{token, nombre, rol, usuario_id}`
- El rol determina el flujo siguiente: admin → admin panel, capturista → socioeconomico, tecnico → tecnica

### Módulo 2 — Estudio Socioeconómico (`socioeconomico.html`)

Captura en un solo formulario:

**Datos del beneficiario:**
nombre, fecha de nacimiento, diagnóstico médico, domicilio completo (calle, colonia, ciudad), teléfonos

**Datos de tutores (1 obligatorio, 2 opcional):**
nombre, edad, nivel de estudios, estado civil, número de hijos, tipo de vivienda, fuente de empleo, antigüedad, ingreso mensual, afiliación IMSS / INFONAVIT

**Cierre del estudio:**
otras fuentes de ingreso, historial previo de silla de ruedas, elaboró el estudio, fecha, sede

Soporta **guardar borrador** (status `borrador`) para continuar después, y **guardar estudio** (status `completo`) para avanzar al módulo técnico.

### Módulo 3 — Solicitud Técnica (`tecnica.html`)

- **Entorno de uso:** Urbano / Rural / Mixto
- **Capacidad postural:** control de tronco, control de cabeza, observaciones clínicas (escoliosis, etc.)
- **Medidas corporales** (en pulgadas): altura total, peso, cabeza–asiento, hombro–asiento, profundidad asiento, rodilla–talón, ancho de cadera
- **Fotografía clínica:** upload de JPG/PNG hasta 10 MB (guardada con nombre UUID)
- **Gestión:** entidad solicitante, prioridad (Alta / Media), justificación

---

## API — Endpoints

Todos los endpoints (excepto `/api/auth/login` y `/api/health`) requieren `Authorization: Bearer <token>`.

| Método | Ruta | Rol requerido | Descripción |
|---|---|---|---|
| `GET` | `/` | — | Health check |
| `GET` | `/api/health` | — | Health check detallado |
| `POST` | `/api/auth/login` | — | Autenticación JWT (email + password) |
| `GET` | `/api/auth/me` | auth | Obtener usuario actual |
| `POST` | `/api/estudios` | capturista, admin | Crear estudio socioeconómico completo |
| `PATCH` | `/api/estudios/{id}` | owner, admin | Actualizar campos del estudio |
| `GET` | `/api/estudios/{id}` | owner, admin | Obtener estudio con beneficiario y tutores |
| `POST` | `/api/upload-foto` | tecnico, admin | Subir imagen (JPG/PNG ≤ 10 MB) → retorna `foto_path` |
| `POST` | `/api/solicitudes` | tecnico, admin | Crear solicitud técnica |
| `PATCH` | `/api/solicitudes/{id}` | owner, admin | Actualizar solicitud técnica |
| `GET` | `/api/solicitudes/{id}` | owner, admin | Obtener solicitud técnica por ID |
| `GET` | `/api/solicitudes/{id}/foto` | owner, admin | Obtener signed URL para foto técnica |
| `POST` | `/api/usuarios` | admin | Crear usuario del sistema |
| `GET` | `/api/usuarios` | admin | Listar usuarios |
| `DELETE` | `/api/usuarios/{id}` | admin | Desactivar usuario (soft delete) |
| `POST` | `/api/paises` | admin | Crear país |
| `GET` | `/api/paises` | auth | Listar países |
| `POST` | `/api/regiones` | admin | Crear región |
| `GET` | `/api/regiones` | auth | Listar regiones |

### Ejemplo — Crear estudio socioeconómico

```bash
# 1. Obtener token JWT
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"capturista@test.mx","password":"password123"}' \
  | jq -r '.access_token')

# 2. Crear estudio con autenticación
curl -X POST http://localhost:8000/api/estudios \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "region_id": 1,
    "sede": "León sede Forum",
    "beneficiario": {
      "nombre": "Ana García López",
      "fecha_nacimiento": "1990-05-15",
      "diagnostico": "Parálisis cerebral",
      "calle": "Av. López Mateos 123",
      "colonia": "Centro",
      "ciudad": "León",
      "telefonos": "4621234567"
    },
    "tutores": [{
      "numero_tutor": 1,
      "nombre": "Carlos García",
      "edad": 45,
      "ingreso_mensual": 8000,
      "tiene_imss": true,
      "tiene_infonavit": false
    }],
    "estudio": {
      "tuvo_silla_previa": false,
      "elaboro_estudio": "Capturista Ejemplo",
      "fecha_estudio": "2026-03-26",
      "status": "completo"
    }
  }'
```

---

## Base de datos

PostgreSQL vía Supabase (producción). En desarrollo se requiere `DB_HOST`, `DB_PASSWORD` y demás variables de entorno.

```
usuarios
├── id  ·  nombre  ·  email  ·  password_hash  ·  rol  ·  activo

paises
├── id  ·  nombre  ·  codigo  ·  activo

regiones  ──→  paises
├── id  ·  pais_id  ·  nombre  ·  codigo  ·  activo

region_counters
├── pais_codigo  ·  region_codigo  ·  anio  ·  ultimo_numero

beneficiarios  ──→  regiones
├── id  ·  nombre  ·  fecha_nacimiento  ·  diagnostico
└── calle  ·  colonia  ·  ciudad  ·  telefonos  ·  email
    folio  ·  region_id  ·  sede

tutores  ──→  beneficiarios
├── id  ·  beneficiario_id  ·  numero_tutor (1 o 2)
└── nombre  ·  edad  ·  nivel_estudios  ·  estado_civil
    vivienda  ·  fuente_empleo  ·  ingreso_mensual
    tiene_imss  ·  tiene_infonavit

estudios_socioeconomicos  ──→  beneficiarios + usuarios
├── id  ·  beneficiario_id  ·  usuario_id
└── sede  ·  fecha_estudio  ·  otras_fuentes_ingreso
    tuvo_silla_previa  ·  status (borrador | completo)

solicitudes_tecnicas  ──→  beneficiarios + usuarios
├── id  ·  beneficiario_id  ·  usuario_id
└── entorno  ·  control_tronco  ·  control_cabeza
    altura_total_in  ·  peso_kg  ·  5 medidas en pulgadas
    foto_url  ·  foto_path  ·  prioridad (Alta | Media)  ·  status
```

> **Nota:** Los campos `capturista_id` en `estudios_socioeconomicos` y `solicitudes_tecnicas`
> permanecen en la base de datos real por compatibilidad temporal, pero el código v2 usa
> exclusivamente `usuario_id`. Serán eliminados en una migración futura.

---

## Seguridad

| Aspecto | Implementación |
|---|---|
| Autenticación | JWT HS256, 8h expiración, `python-jose` + `passlib[bcrypt]` |
| Autorización | RBAC server-side (`require_roles`) en todos los endpoints protegidos |
| Upload de imágenes | Validación doble: MIME type + extensión (solo `.jpg` / `.png`) |
| Tamaño de archivos | Límite de 10 MB por imagen rechazado en backend |
| Almacenamiento | Supabase Storage bucket privado, signed URLs temporales |
| Campos numéricos | Validación Pydantic + constraints en PostgreSQL (edad, medidas, ingresos) |
| Integridad referencial | Foreign keys activas en PostgreSQL |
| CORS | Configurado en `main.py` — restringir origins en producción |
| Headers de seguridad | X-Frame-Options, X-Content-Type-Options, Cache-Control |
| Docs en producción | `/docs`, `/redoc`, `/openapi.json` desactivados cuando `ENV=production` |

---

## Roadmap

- [x] Migrar SQLite → Supabase (PostgreSQL)
- [x] Migrar `uploads/` → Supabase Storage bucket
- [x] Implementar JWT con expiración para reemplazar login por nombre
- [x] RBAC server-side (`require_roles`) en todos los endpoints
- [x] Security headers y cache policy en producción
- [x] Bucket privado con signed URLs para fotos técnicas
- [ ] Eliminar columnas `capturista_id` legacy de la base de datos
- [ ] Verificar Python 3.12 en el entorno de despliegue

---

## Desarrollado por NEUXORA

<div align="center">

**[NEUXORA — Agencia de Tecnología e IA](https://andreraz.github.io/)**

*Hacemos posible lo imposible, porque lo difícil lo puede hacer cualquiera.*

León, Guanajuato, México &nbsp;·&nbsp; Lun–Sab 9:00–20:00

| | |
|---|---|
| 📞 Teléfono / WhatsApp | [+52 462 272 2089](https://wa.me/524622722089) |
| 📧 Email | [cmed.beta@gmail.com](mailto:cmed.beta@gmail.com) |
| 🌐 Web | [andreraz.github.io](https://andreraz.github.io/) |

<br/>

| Departamento | Especialidad |
|---|---|
| **C-MED** | Apps médicas, expedientes clínicos, dispositivos personalizados con trazabilidad |
| **EDU-IA** | Plataformas educativas adaptativas con IA y analítica en tiempo real |
| **Investigación** | Modelos ML/DL, visión por computadora, simulaciones científicas |

<br/>

*Proyecto desarrollado para el programa **Ecosistema VIDA UG** —*
*Universidad de Guanajuato en colaboración con Rotary 200.*

</div>
