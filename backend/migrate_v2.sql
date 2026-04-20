-- =============================================================================
-- LEGACY / DO NOT EXECUTE
-- =============================================================================
-- Este archivo queda deprecado por seguridad.
-- Motivo: contenía operaciones destructivas (`TRUNCATE ... CASCADE`) no seguras.
-- Regla vigente: usar solo migraciones incrementales en `backend/migrations/`.
-- =============================================================================

DO $$
BEGIN
    RAISE EXCEPTION
        'LEGACY SCRIPT - DO NOT EXECUTE: use backend/migrations/* incremental migrations only.';
END
$$;
