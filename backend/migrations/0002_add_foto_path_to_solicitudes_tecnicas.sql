-- 0002_add_foto_path_to_solicitudes_tecnicas.sql
-- Objetivo:
--   1) agregar columna canónica foto_path
--   2) mantener compatibilidad temporal con foto_url
--   3) dejar backfill incremental y re-ejecutable

ALTER TABLE public.solicitudes_tecnicas
ADD COLUMN IF NOT EXISTS foto_path TEXT;

-- Backfill mínimo para URLs históricas de Storage público o signed URLs.
-- Ejemplos soportados:
--   https://<ref>.supabase.co/storage/v1/object/public/fotos-tecnica/a/b.png
--   https://<ref>.supabase.co/storage/v1/object/sign/fotos-tecnica/a/b.png?token=...
UPDATE solicitudes_tecnicas
SET foto_path = regexp_replace(split_part(foto_url, '/fotos-tecnica/', 2), '\\?.*$', '')
WHERE foto_path IS NULL
  AND foto_url IS NOT NULL
  AND foto_url LIKE '%/fotos-tecnica/%';

-- Compatibilidad dual-write:
-- durante la transición la app seguirá guardando foto_url derivada
-- como storage://fotos-tecnica/<foto_path>
