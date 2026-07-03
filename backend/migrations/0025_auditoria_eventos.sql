-- Issue #75: security audit trail for signed URLs, exports, detail reads, and admin changes.
CREATE TABLE IF NOT EXISTS auditoria_eventos (
    id               BIGSERIAL PRIMARY KEY,
    actor_usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    actor_rol        TEXT NOT NULL,
    accion           TEXT NOT NULL,
    recurso_tipo     TEXT NOT NULL,
    recurso_id       TEXT,
    metadata         JSONB NOT NULL DEFAULT '{}'::jsonb,
    ip               INET,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_auditoria_accion_not_blank CHECK (btrim(accion) <> ''),
    CONSTRAINT chk_auditoria_recurso_tipo_not_blank CHECK (btrim(recurso_tipo) <> '')
);

CREATE INDEX IF NOT EXISTS idx_auditoria_eventos_actor_created
    ON auditoria_eventos(actor_usuario_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_auditoria_eventos_recurso
    ON auditoria_eventos(recurso_tipo, recurso_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_auditoria_eventos_accion_created
    ON auditoria_eventos(accion, created_at DESC);
