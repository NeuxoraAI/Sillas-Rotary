-- ============================================================================
-- Migration: 0022_unify_org_leadership_source.sql
-- Purpose:  Unify the org-leadership source of truth on the
--           organizaciones_lideres TABLE (Issue #53 / #80).
--
-- Background: leadership lived in TWO places that could disagree —
--   * column organizaciones.lider_usuario_id (single leader, legacy)
--   * table  organizaciones_lideres          (multiple leaders, canonical)
-- The backend now reads leadership exclusively from the table. This migration
-- backfills any leader that exists only in the column into the table, so the
-- table becomes the complete source before the column is retired.
--
-- This is ADDITIVE only (per migrations/README.md rule #3): the column is NOT
-- dropped here. A later migration drops organizaciones.lider_usuario_id once
-- this backfill is confirmed in production. See the DEFERRED block below.
-- ============================================================================

BEGIN;

-- Backfill: every non-null column leader missing from the table is inserted.
-- ON CONFLICT guards against rows already present (PK = organizacion_id,usuario_id).
INSERT INTO organizaciones_lideres (organizacion_id, usuario_id)
SELECT o.id, o.lider_usuario_id
FROM organizaciones o
WHERE o.lider_usuario_id IS NOT NULL
ON CONFLICT (organizacion_id, usuario_id) DO NOTHING;

COMMIT;

-- ----------------------------------------------------------------------------
-- DEFERRED (do NOT run in this migration) — retire the legacy column once the
-- backfill above is verified in production and no code reads the column:
--
--   BEGIN;
--   DROP INDEX IF EXISTS public.idx_organizaciones_lider;
--   ALTER TABLE public.organizaciones DROP COLUMN IF EXISTS lider_usuario_id;
--   COMMIT;
--
-- Verification before the drop:
--   SELECT o.id, o.lider_usuario_id
--   FROM organizaciones o
--   LEFT JOIN organizaciones_lideres ol
--     ON ol.organizacion_id = o.id AND ol.usuario_id = o.lider_usuario_id
--   WHERE o.lider_usuario_id IS NOT NULL AND ol.usuario_id IS NULL;
--   -- must return zero rows (every column leader is in the table)
-- ----------------------------------------------------------------------------
