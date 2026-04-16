import os

import psycopg2
from supabase import create_client


DDL = [
    """
    CREATE TABLE IF NOT EXISTS capturistas (
        id              SERIAL PRIMARY KEY,
        nombre          TEXT    NOT NULL CHECK(length(nombre) >= 2) UNIQUE,
        fecha_registro  DATE    NOT NULL DEFAULT CURRENT_DATE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS beneficiarios (
        id                SERIAL PRIMARY KEY,
        nombre            TEXT NOT NULL,
        fecha_nacimiento  TEXT NOT NULL,
        diagnostico       TEXT NOT NULL,
        calle             TEXT NOT NULL,
        colonia           TEXT NOT NULL,
        ciudad            TEXT NOT NULL,
        telefonos         TEXT NOT NULL,
        created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tutores (
        id               SERIAL PRIMARY KEY,
        beneficiario_id  INTEGER NOT NULL REFERENCES beneficiarios(id) ON DELETE CASCADE,
        numero_tutor     INTEGER NOT NULL CHECK(numero_tutor IN (1, 2)),
        nombre           TEXT    NOT NULL,
        edad             INTEGER CHECK(edad IS NULL OR (edad > 0 AND edad < 120)),
        nivel_estudios   TEXT,
        estado_civil     TEXT,
        num_hijos        INTEGER DEFAULT 0,
        vivienda         TEXT    CHECK(vivienda IS NULL OR vivienda IN ('Propia', 'Rentada')),
        fuente_empleo    TEXT,
        antiguedad       TEXT,
        ingreso_mensual  REAL    CHECK(ingreso_mensual IS NULL OR ingreso_mensual >= 0),
        tiene_imss       INTEGER NOT NULL DEFAULT 0 CHECK(tiene_imss IN (0, 1)),
        tiene_infonavit  INTEGER NOT NULL DEFAULT 0 CHECK(tiene_infonavit IN (0, 1)),
        UNIQUE(beneficiario_id, numero_tutor)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS estudios_socioeconomicos (
        id                      SERIAL PRIMARY KEY,
        beneficiario_id         INTEGER NOT NULL REFERENCES beneficiarios(id) ON DELETE RESTRICT,
        capturista_id           INTEGER NOT NULL REFERENCES capturistas(id) ON DELETE RESTRICT,
        otras_fuentes_ingreso   TEXT,
        monto_otras_fuentes     REAL,
        tuvo_silla_previa       INTEGER CHECK(tuvo_silla_previa IN (0, 1)),
        como_obtuvo_silla       TEXT,
        elaboro_estudio         TEXT    NOT NULL,
        fecha_estudio           TEXT    NOT NULL,
        sede                    TEXT    NOT NULL,
        status                  TEXT    NOT NULL DEFAULT 'borrador' CHECK(status IN ('borrador', 'completo')),
        created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS solicitudes_tecnicas (
        id                          SERIAL PRIMARY KEY,
        beneficiario_id             INTEGER NOT NULL REFERENCES beneficiarios(id) ON DELETE RESTRICT,
        capturista_id               INTEGER NOT NULL REFERENCES capturistas(id) ON DELETE RESTRICT,
        entorno                     TEXT    NOT NULL,
        control_tronco              TEXT    NOT NULL,
        control_cabeza              TEXT    NOT NULL,
        observaciones_posturales    TEXT,
        altura_total_in             REAL    CHECK(altura_total_in IS NULL OR altura_total_in > 0),
        peso_kg                     REAL    CHECK(peso_kg IS NULL OR peso_kg > 0),
        medida_cabeza_asiento       REAL    CHECK(medida_cabeza_asiento IS NULL OR medida_cabeza_asiento > 0),
        medida_hombro_asiento       REAL    CHECK(medida_hombro_asiento IS NULL OR medida_hombro_asiento > 0),
        medida_prof_asiento         REAL    CHECK(medida_prof_asiento IS NULL OR medida_prof_asiento > 0),
        medida_rodilla_talon        REAL    CHECK(medida_rodilla_talon IS NULL OR medida_rodilla_talon > 0),
        medida_ancho_cadera         REAL    CHECK(medida_ancho_cadera IS NULL OR medida_ancho_cadera > 0),
        foto_url                    TEXT,
        entidad_solicitante         TEXT,
        prioridad                   TEXT    CHECK(prioridad IS NULL OR prioridad IN ('Alta', 'Media')),
        justificacion               TEXT,
        status                      TEXT    NOT NULL DEFAULT 'borrador' CHECK(status IN ('borrador', 'completo')),
        created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_tutores_beneficiario ON tutores(beneficiario_id)",
    "CREATE INDEX IF NOT EXISTS idx_estudios_beneficiario ON estudios_socioeconomicos(beneficiario_id)",
    "CREATE INDEX IF NOT EXISTS idx_estudios_capturista ON estudios_socioeconomicos(capturista_id)",
    "CREATE INDEX IF NOT EXISTS idx_solicitudes_beneficiario ON solicitudes_tecnicas(beneficiario_id)",
    "CREATE INDEX IF NOT EXISTS idx_solicitudes_capturista ON solicitudes_tecnicas(capturista_id)",
]


def init() -> None:
    conn = psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ.get("DB_NAME", "postgres"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ["DB_PASSWORD"],
        sslmode="require",
    )
    try:
        with conn.cursor() as cur:
            for statement in DDL:
                cur.execute(statement)
        conn.commit()
    finally:
        conn.close()

    _init_storage()


def _init_storage() -> None:
    client = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
    )
    try:
        client.storage.create_bucket("fotos-tecnica", options={"public": True})
        print("Storage bucket 'fotos-tecnica' created.")
    except Exception:
        print("Storage bucket 'fotos-tecnica' already exists — skipping.")


if __name__ == "__main__":
    init()
    print("Database initialized successfully.")
