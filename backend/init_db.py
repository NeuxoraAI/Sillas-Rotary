import os

import psycopg2
from supabase import create_client


DDL = [
    # -----------------------------------------------------------------------
    # LEGACY v1 — REMOVED: capturistas table replaced by `usuarios` (v2)
    # The column `capturista_id` in estudios_socioeconomicos and
    # solicitudes_tecnicas is retained in the live DB for backward
    # compatibility but is no longer created by this script.
    # -----------------------------------------------------------------------
    """
    CREATE TABLE IF NOT EXISTS beneficiarios (
        id                SERIAL PRIMARY KEY,
        nombre            TEXT,
        nombres           TEXT,
        apellido_paterno  TEXT,
        apellido_materno  TEXT,
        fecha_nacimiento  TEXT,
        diagnostico       TEXT,
        calle             TEXT,
        num_ext           TEXT,
        num_int           TEXT,
        colonia           TEXT,
        ciudad            TEXT,
        estado_codigo     TEXT,
        estado_nombre     TEXT,
        sexo                         TEXT,
        telefonos                    TEXT,
        created_at                     TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tutores (
        id               SERIAL PRIMARY KEY,
        beneficiario_id  INTEGER NOT NULL REFERENCES beneficiarios(id) ON DELETE CASCADE,
        numero_tutor     INTEGER NOT NULL CHECK(numero_tutor IN (1, 2)),
        nombre           TEXT,
        email            TEXT,
        edad             INTEGER CHECK(edad IS NULL OR (edad > 0 AND edad < 120)),
        nivel_estudios   TEXT,
        estado_civil     TEXT,
        num_hijos        INTEGER DEFAULT 0,
        vivienda         TEXT    CHECK(vivienda IS NULL OR vivienda IN ('Propia', 'Rentada')),
        fuente_empleo    TEXT,
        antiguedad       TEXT,
        ingreso_mensual  REAL    CHECK(ingreso_mensual IS NULL OR ingreso_mensual >= 0),
        antiguedad_meses INTEGER,
        antiguedad_aplica INTEGER NOT NULL DEFAULT 1 CHECK(antiguedad_aplica IN (0,1)),
        sin_empleo       INTEGER NOT NULL DEFAULT 0 CHECK(sin_empleo IN (0,1)),
        otras_fuentes_aplica INTEGER NOT NULL DEFAULT 0 CHECK(otras_fuentes_aplica IN (0,1)),
        otras_fuentes_ingreso TEXT,
        monto_otras_fuentes REAL,
        tiene_imss       INTEGER CHECK(tiene_imss IS NULL OR tiene_imss IN (0, 1)),
        tiene_infonavit  INTEGER CHECK(tiene_infonavit IS NULL OR tiene_infonavit IN (0, 1)),
        UNIQUE(beneficiario_id, numero_tutor)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS estudios_socioeconomicos (
        id                      SERIAL PRIMARY KEY,
        beneficiario_id         INTEGER NOT NULL REFERENCES beneficiarios(id) ON DELETE RESTRICT,
        usuario_id              INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
        -- DEPRECATED v1: capturista_id column retained in live DB for backward
        -- compatibility.  New code uses usuario_id (managed by Supabase migrations).
        -- capturista_id       INTEGER REFERENCES capturistas(id) ON DELETE RESTRICT,
        otras_fuentes_ingreso   TEXT,
        monto_otras_fuentes     REAL,
        tuvo_silla_previa       INTEGER CHECK(tuvo_silla_previa IN (0, 1)),
        como_obtuvo_silla       TEXT,
        elaboro_estudio         TEXT,
        fecha_estudio           TEXT,
        sede                    TEXT,
        ciudad_registro         TEXT,
        credencial_path         TEXT,
        credencial_url          TEXT,
        comprobante_domicilio_path TEXT,
        comprobante_domicilio_url  TEXT,
        status                  TEXT    NOT NULL DEFAULT 'borrador' CHECK(status IN ('borrador', 'completo')),
        finalizado_at           TIMESTAMPTZ NULL,
        created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_estudio_beneficiario_usuario UNIQUE (beneficiario_id, usuario_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS solicitudes_tecnicas (
        id                          SERIAL PRIMARY KEY,
        beneficiario_id             INTEGER NOT NULL REFERENCES beneficiarios(id) ON DELETE RESTRICT,
        usuario_id                  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
        -- DEPRECATED v1: capturista_id column retained in live DB for backward
        -- compatibility.  New code uses usuario_id (managed by Supabase migrations).
        -- capturista_id           INTEGER REFERENCES capturistas(id) ON DELETE RESTRICT,
        entorno                     TEXT,
        control_tronco              TEXT,
        control_cabeza              TEXT,
        control_de_piernas          TEXT,
        padecimiento    TEXT,
        altura_total_in             NUMERIC(7,3) CHECK(altura_total_in IS NULL OR (altura_total_in >= 0 AND altura_total_in <= 9999.999)),
        peso_kg                     NUMERIC(7,3) CHECK(peso_kg IS NULL OR (peso_kg >= 0 AND peso_kg <= 9999.999)),
        medida_cabeza_asiento       NUMERIC(7,3) CHECK(medida_cabeza_asiento IS NULL OR (medida_cabeza_asiento >= 0 AND medida_cabeza_asiento <= 9999.999)),
        medida_hombro_asiento       NUMERIC(7,3) CHECK(medida_hombro_asiento IS NULL OR (medida_hombro_asiento >= 0 AND medida_hombro_asiento <= 9999.999)),
        medida_prof_asiento         NUMERIC(7,3) CHECK(medida_prof_asiento IS NULL OR (medida_prof_asiento >= 0 AND medida_prof_asiento <= 9999.999)),
        medida_rodilla_talon        NUMERIC(7,3) CHECK(medida_rodilla_talon IS NULL OR (medida_rodilla_talon >= 0 AND medida_rodilla_talon <= 9999.999)),
        medida_ancho_cadera         NUMERIC(7,3) CHECK(medida_ancho_cadera IS NULL OR (medida_ancho_cadera >= 0 AND medida_ancho_cadera <= 9999.999)),
        unidad_captura              TEXT    DEFAULT 'in',
        foto_url                    TEXT,
        foto_path                   TEXT,
        entidad_solicitante         TEXT,
        prioridad                   TEXT    CHECK(prioridad IS NULL OR prioridad IN ('Alta', 'Media')),
        justificacion               TEXT,
        status                      TEXT    NOT NULL DEFAULT 'borrador' CHECK(status IN ('borrador', 'completo')),
        finalizado_at               TIMESTAMPTZ NULL,
        created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_solicitud_beneficiario_usuario UNIQUE (beneficiario_id, usuario_id)
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS procesos_tecnicos (
        id                            SERIAL PRIMARY KEY,
        beneficiario_id               INTEGER NOT NULL REFERENCES beneficiarios(id) ON DELETE RESTRICT,
        estado                        TEXT NOT NULL DEFAULT 'sin_iniciar'
                                      CHECK(estado IN ('sin_iniciar', 'en_proceso', 'finalizado', 'revision_pendiente')),
        responsable_actual_usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
        tecnico_inicio_usuario_id     INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
        fecha_inicio                  TIMESTAMPTZ,
        fecha_ultimo_movimiento       TIMESTAMPTZ,
        revision_pendiente            BOOLEAN NOT NULL DEFAULT FALSE,
        pdf_snapshot_json             JSONB,
        created_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(beneficiario_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS procesos_tecnicos_participantes (
        id                 SERIAL PRIMARY KEY,
        proceso_tecnico_id INTEGER NOT NULL REFERENCES procesos_tecnicos(id) ON DELETE CASCADE,
        usuario_id         INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
        accion             TEXT NOT NULL CHECK(accion IN ('inicio', 'continuacion', 'finalizacion', 'revision')),
        created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_tutores_beneficiario ON tutores(beneficiario_id)",
    "CREATE INDEX IF NOT EXISTS idx_estudios_beneficiario ON estudios_socioeconomicos(beneficiario_id)",
    # DEPRECATED v1: legacy index on capturista_id — retained in live DB, not created by init_db.py
    # "CREATE INDEX IF NOT EXISTS idx_estudios_capturista ON estudios_socioeconomicos(capturista_id)",
    "CREATE INDEX IF NOT EXISTS idx_solicitudes_beneficiario ON solicitudes_tecnicas(beneficiario_id)",
    "CREATE INDEX IF NOT EXISTS idx_procesos_tecnicos_beneficiario ON procesos_tecnicos(beneficiario_id)",
    "CREATE INDEX IF NOT EXISTS idx_procesos_tecnicos_estado ON procesos_tecnicos(estado)",
    "CREATE INDEX IF NOT EXISTS idx_procesos_participantes_proceso ON procesos_tecnicos_participantes(proceso_tecnico_id)",
    "CREATE INDEX IF NOT EXISTS idx_procesos_participantes_usuario ON procesos_tecnicos_participantes(usuario_id)",
    "CREATE INDEX IF NOT EXISTS idx_procesos_participantes_created_at ON procesos_tecnicos_participantes(created_at)",
    # DEPRECATED v1: legacy index on capturista_id — retained in live DB, not created by init_db.py
    # "CREATE INDEX IF NOT EXISTS idx_solicitudes_capturista ON solicitudes_tecnicas(capturista_id)",

    # -----------------------------------------------------------------------
    # Perfiles / GitHub-style profiles (v2)
    # -----------------------------------------------------------------------
    """
    CREATE TABLE IF NOT EXISTS organizaciones (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        direccion TEXT,
        telefono TEXT,
        email TEXT,
        usuario_id INTEGER UNIQUE REFERENCES usuarios(id) ON DELETE RESTRICT,
        lider_usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
        activo BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_organizaciones_usuario_id ON organizaciones(usuario_id)",
    "CREATE INDEX IF NOT EXISTS idx_organizaciones_lider ON organizaciones(lider_usuario_id)",
    "CREATE INDEX IF NOT EXISTS idx_organizaciones_activo ON organizaciones(activo)",
    """
    CREATE TABLE IF NOT EXISTS organizaciones_lideres (
        organizacion_id  INTEGER NOT NULL REFERENCES organizaciones(id) ON DELETE CASCADE,
        usuario_id       INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
        created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (organizacion_id, usuario_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS organizaciones_miembros (
        organizacion_id  INTEGER NOT NULL REFERENCES organizaciones(id) ON DELETE CASCADE,
        usuario_id       INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
        created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (organizacion_id, usuario_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_org_miembros_usuario ON organizaciones_miembros(usuario_id)",
    """
    CREATE TABLE IF NOT EXISTS organizaciones_voluntarios (
        id               SERIAL PRIMARY KEY,
        organizacion_id  INTEGER NOT NULL REFERENCES organizaciones(id) ON DELETE CASCADE,
        nombre           TEXT NOT NULL,
        contacto         TEXT,
        capturas_count   INTEGER NOT NULL DEFAULT 0,
        ultima_captura   TIMESTAMPTZ,
        created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (organizacion_id, nombre)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_org_voluntarios_org ON organizaciones_voluntarios(organizacion_id)",
    "CREATE INDEX IF NOT EXISTS idx_estudios_usuario_created ON estudios_socioeconomicos(usuario_id, created_at)",
    "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS telefono TEXT",
    "ALTER TABLE estudios_socioeconomicos ADD COLUMN IF NOT EXISTS finalizado_at TIMESTAMPTZ NULL",
    "ALTER TABLE solicitudes_tecnicas ADD COLUMN IF NOT EXISTS finalizado_at TIMESTAMPTZ NULL",
    "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS avatar_url TEXT",
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
    _ensure_private_bucket(
        client,
        bucket_name="fotos-tecnica",
        allowed_mime_types=["image/jpeg", "image/png"],
    )
    _ensure_private_bucket(
        client,
        bucket_name="documentos-estudio",
        allowed_mime_types=["image/jpeg", "image/png", "application/pdf"],
    )


def _ensure_private_bucket(client, *, bucket_name: str, allowed_mime_types: list[str]) -> None:
    secure_options = {
        "public": False,
        "allowed_mime_types": allowed_mime_types,
        "file_size_limit": 10 * 1024 * 1024,
    }

    try:
        bucket = client.storage.get_bucket(bucket_name)
        if not isinstance(bucket, dict) or bucket.get("public") is not False:
            client.storage.update_bucket(bucket_name, options=secure_options)
            print(f"Storage bucket '{bucket_name}' hardened to private mode.")
        else:
            client.storage.update_bucket(bucket_name, options=secure_options)
            print(f"Storage bucket '{bucket_name}' already private — security options refreshed.")
    except Exception:
        client.storage.create_bucket(bucket_name, options=secure_options)
        print(f"Storage bucket '{bucket_name}' created in private mode.")


if __name__ == "__main__":
    init()
    print("Database initialized successfully.")
