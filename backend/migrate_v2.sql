-- =============================================================================
-- Sillas Rotary v2 Migration
-- PRD v2 — Fase 1: Fundación
-- Run this ONCE on Supabase SQL editor before deploying v2.
-- WARNING: TRUNCATES all existing data (test data only — production wipe)
-- =============================================================================

-- Step 1: Truncate all existing data (preserves structure)
TRUNCATE TABLE
    solicitudes_tecnicas,
    estudios_socioeconomicos,
    tutores,
    beneficiarios,
    capturistas
CASCADE;

-- Step 2: New tables -------------------------------------------------------

CREATE TABLE IF NOT EXISTS usuarios (
    id              SERIAL PRIMARY KEY,
    nombre          TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    rol             TEXT NOT NULL DEFAULT 'capturista'
                        CHECK(rol IN ('admin', 'capturista', 'tecnico')),
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS paises (
    id      SERIAL PRIMARY KEY,
    nombre  TEXT NOT NULL UNIQUE,    -- "México", "USA"
    codigo  TEXT NOT NULL UNIQUE,    -- "MX", "US"
    activo  BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS regiones (
    id       SERIAL PRIMARY KEY,
    pais_id  INTEGER NOT NULL REFERENCES paises(id),
    nombre   TEXT NOT NULL,          -- "León, Gto", "Pearland, TX"
    codigo   TEXT NOT NULL,          -- "LON", "PRL" — 3 chars
    activo   BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(pais_id, codigo)
);

CREATE TABLE IF NOT EXISTS region_counters (
    pais_codigo    TEXT NOT NULL,
    region_codigo  TEXT NOT NULL,
    anio           INTEGER NOT NULL,
    ultimo_numero  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (pais_codigo, region_codigo, anio)
);

-- Step 3: Alter existing tables --------------------------------------------

-- beneficiarios: add folio, region, sede, email
ALTER TABLE beneficiarios
    ADD COLUMN IF NOT EXISTS folio      TEXT UNIQUE,
    ADD COLUMN IF NOT EXISTS region_id  INTEGER REFERENCES regiones(id),
    ADD COLUMN IF NOT EXISTS sede       TEXT,
    ADD COLUMN IF NOT EXISTS email      TEXT;

-- tutores: add email
ALTER TABLE tutores
    ADD COLUMN IF NOT EXISTS email TEXT;

-- solicitudes_tecnicas: add chair status
ALTER TABLE solicitudes_tecnicas
    ADD COLUMN IF NOT EXISTS estado_silla   TEXT NOT NULL DEFAULT 'registrada'
        CHECK(estado_silla IN ('registrada', 'en_proceso', 'lista', 'entregada')),
    ADD COLUMN IF NOT EXISTS lugar_entrega  TEXT,
    ADD COLUMN IF NOT EXISTS fecha_entrega  DATE;

-- Step 4: Replace capturista_id FK with usuario_id in both tables ---------

-- estudios_socioeconomicos
ALTER TABLE estudios_socioeconomicos
    DROP CONSTRAINT IF EXISTS estudios_socioeconomicos_capturista_id_fkey,
    ADD COLUMN IF NOT EXISTS usuario_id INTEGER REFERENCES usuarios(id);

-- solicitudes_tecnicas
ALTER TABLE solicitudes_tecnicas
    DROP CONSTRAINT IF EXISTS solicitudes_tecnicas_capturista_id_fkey,
    ADD COLUMN IF NOT EXISTS usuario_id INTEGER REFERENCES usuarios(id);

-- Step 5: Historial de estados (Fase 4 — create now, use later) -----------

CREATE TABLE IF NOT EXISTS historial_estados (
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

-- Step 6: Indexes ----------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_regiones_pais ON regiones(pais_id);
CREATE INDEX IF NOT EXISTS idx_beneficiarios_folio ON beneficiarios(folio);
CREATE INDEX IF NOT EXISTS idx_beneficiarios_region ON beneficiarios(region_id);
CREATE INDEX IF NOT EXISTS idx_estudios_usuario ON estudios_socioeconomicos(usuario_id);
CREATE INDEX IF NOT EXISTS idx_solicitudes_usuario ON solicitudes_tecnicas(usuario_id);
CREATE INDEX IF NOT EXISTS idx_solicitudes_estado ON solicitudes_tecnicas(estado_silla);
CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email);
