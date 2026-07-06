-- 0023: Drop dead columns confirmed by the 2026-07-01 code + DB audit.
-- All had 0 non-null rows and no runtime writer:
--   * beneficiarios.folio: legacy identifier, superseded by curp_benef
--     (Issue #32); read-only fallback in code, removed alongside this drop.
--   * solicitudes_tecnicas.estado_silla / lugar_entrega / fecha_entrega:
--     unshipped delivery-tracking design, never wired.
--   * solicitudes_tecnicas.requiere_soporte_oxigeno: superseded by
--     soporte_oxigeno (migration 0018).
--   * tutores.antiguedad: superseded by antiguedad_meses.
--   * estudios_socioeconomicos.otras_fuentes_ingreso / monto_otras_fuentes:
--     these live on tutores, the estudios copies were never written.
-- Applied to Supabase on 2026-07-01 via MCP migration drop_dead_columns.

ALTER TABLE public.beneficiarios
    DROP COLUMN IF EXISTS folio;

ALTER TABLE public.solicitudes_tecnicas
    DROP COLUMN IF EXISTS estado_silla,
    DROP COLUMN IF EXISTS lugar_entrega,
    DROP COLUMN IF EXISTS fecha_entrega,
    DROP COLUMN IF EXISTS requiere_soporte_oxigeno;

ALTER TABLE public.tutores
    DROP COLUMN IF EXISTS antiguedad;

ALTER TABLE public.estudios_socioeconomicos
    DROP COLUMN IF EXISTS otras_fuentes_ingreso,
    DROP COLUMN IF EXISTS monto_otras_fuentes;
