-- 0022: Persist two fields the UI already collects but never stored.
--   * equipo_solicitado: requested equipment type (select in tecnica form).
--   * estudio_clinico_path/url: clinical study document uploaded from the
--     tecnica form (mirrors foto_path/foto_url; stored in the
--     documentos-estudio bucket).
-- Applied to Supabase on 2026-07-01 via MCP migration
-- add_equipo_solicitado_estudio_clinico.

ALTER TABLE public.solicitudes_tecnicas
    ADD COLUMN IF NOT EXISTS equipo_solicitado text,
    ADD COLUMN IF NOT EXISTS estudio_clinico_path text,
    ADD COLUMN IF NOT EXISTS estudio_clinico_url text;
