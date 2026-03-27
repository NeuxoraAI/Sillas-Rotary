import sqlite3


DDL = [
    """
    CREATE TABLE IF NOT EXISTS capturistas (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre          TEXT    NOT NULL CHECK(length(nombre) >= 2),
        fecha_registro  TEXT    NOT NULL DEFAULT (date('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS beneficiarios (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre            TEXT NOT NULL,
        fecha_nacimiento  TEXT NOT NULL,
        diagnostico       TEXT NOT NULL,
        calle             TEXT NOT NULL,
        colonia           TEXT NOT NULL,
        ciudad            TEXT NOT NULL,
        telefonos         TEXT NOT NULL,
        created_at        TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tutores (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
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
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        beneficiario_id         INTEGER NOT NULL REFERENCES beneficiarios(id) ON DELETE RESTRICT,
        capturista_id           INTEGER NOT NULL REFERENCES capturistas(id) ON DELETE RESTRICT,
        otras_fuentes_ingreso   TEXT,
        monto_otras_fuentes     REAL    NOT NULL DEFAULT 0,
        tuvo_silla_previa       INTEGER CHECK(tuvo_silla_previa IN (0, 1)),
        como_obtuvo_silla       TEXT,
        elaboro_estudio         TEXT    NOT NULL,
        fecha_estudio           TEXT    NOT NULL,
        sede                    TEXT    NOT NULL,
        status                  TEXT    NOT NULL DEFAULT 'borrador' CHECK(status IN ('borrador', 'completo')),
        created_at              TEXT    NOT NULL DEFAULT (datetime('now')),
        updated_at              TEXT    NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS solicitudes_tecnicas (
        id                          INTEGER PRIMARY KEY AUTOINCREMENT,
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
        created_at                  TEXT    NOT NULL DEFAULT (datetime('now')),
        updated_at                  TEXT    NOT NULL DEFAULT (datetime('now'))
    )
    """,
    # Indexes on FK columns
    "CREATE INDEX IF NOT EXISTS idx_tutores_beneficiario ON tutores(beneficiario_id)",
    "CREATE INDEX IF NOT EXISTS idx_estudios_beneficiario ON estudios_socioeconomicos(beneficiario_id)",
    "CREATE INDEX IF NOT EXISTS idx_estudios_capturista ON estudios_socioeconomicos(capturista_id)",
    "CREATE INDEX IF NOT EXISTS idx_solicitudes_beneficiario ON solicitudes_tecnicas(beneficiario_id)",
    "CREATE INDEX IF NOT EXISTS idx_solicitudes_capturista ON solicitudes_tecnicas(capturista_id)",
]


def init() -> None:
    conn = sqlite3.connect("sillas.db")
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        for statement in DDL:
            conn.execute(statement)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init()
    print("Database initialized successfully.")
