-- 0017_add_finalizado_at.sql
-- Objetivo:
--   Agregar columna finalizado_at a estudios_socioeconomicos y solicitudes_tecnicas
--   para registrar el timestamp de finalización (transición borrador → completo).
--   NULL por defecto para compatibilidad con registros existentes.

ALTER TABLE public.estudios_socioeconomicos
ADD COLUMN IF NOT EXISTS finalizado_at TIMESTAMPTZ NULL;

ALTER TABLE public.solicitudes_tecnicas
ADD COLUMN IF NOT EXISTS finalizado_at TIMESTAMPTZ NULL;
