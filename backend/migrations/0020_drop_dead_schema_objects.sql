-- ============================================================================
-- Migration: 0020_drop_dead_schema_objects.sql
-- Purpose:  Remove confirmed-dead v1 schema objects.
--
-- Objects removed:
--   - historial_estados: abandoned audit idea, unused by runtime
--   - capturistas: legacy table replaced by usuarios.rol = 'capturista'
--   - capturista_id columns: legacy FKs replaced by usuario_id
--   - indexes on capturista_id flagged as unused
--
-- Preconditions verified in production before applying:
--   SELECT COUNT(*) FROM public.historial_estados;
--   SELECT COUNT(*) FROM public.capturistas;
--   SELECT COUNT(*) FROM public.estudios_socioeconomicos WHERE capturista_id IS NOT NULL;
--   SELECT COUNT(*) FROM public.solicitudes_tecnicas WHERE capturista_id IS NOT NULL;
-- ============================================================================

BEGIN;

DROP INDEX IF EXISTS public.idx_estudios_capturista;
DROP INDEX IF EXISTS public.idx_solicitudes_capturista;

ALTER TABLE IF EXISTS public.estudios_socioeconomicos
  DROP COLUMN IF EXISTS capturista_id;

ALTER TABLE IF EXISTS public.solicitudes_tecnicas
  DROP COLUMN IF EXISTS capturista_id;

DROP TABLE IF EXISTS public.historial_estados;
DROP TABLE IF EXISTS public.capturistas;

COMMIT;
