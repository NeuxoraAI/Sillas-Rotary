-- 0012: Tables referenced by the organization endpoints but never created.
-- organizaciones_miembros: org membership (any active app user: admin,
-- tecnico, capturista). organizaciones_voluntarios: guest capturers that
-- register name + phone before capturing through the org account.

CREATE TABLE IF NOT EXISTS organizaciones_miembros (
    organizacion_id  INTEGER NOT NULL REFERENCES organizaciones(id) ON DELETE CASCADE,
    usuario_id       INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (organizacion_id, usuario_id)
);

CREATE INDEX IF NOT EXISTS idx_org_miembros_usuario ON organizaciones_miembros(usuario_id);

CREATE TABLE IF NOT EXISTS organizaciones_voluntarios (
    id               SERIAL PRIMARY KEY,
    organizacion_id  INTEGER NOT NULL REFERENCES organizaciones(id) ON DELETE CASCADE,
    nombre           TEXT NOT NULL,
    contacto         TEXT,
    capturas_count   INTEGER NOT NULL DEFAULT 0,
    ultima_captura   TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (organizacion_id, nombre)
);

CREATE INDEX IF NOT EXISTS idx_org_voluntarios_org ON organizaciones_voluntarios(organizacion_id);
