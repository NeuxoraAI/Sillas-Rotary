-- 0004_add_documento_refs_to_estudios_socioeconomicos.sql
-- Objetivo:
--   1) agregar referencias canónicas para credencial y comprobante de domicilio
--   2) permitir dual-write path/url para compatibilidad con respuestas del frontend

ALTER TABLE public.estudios_socioeconomicos
ADD COLUMN IF NOT EXISTS credencial_path TEXT,
ADD COLUMN IF NOT EXISTS credencial_url TEXT,
ADD COLUMN IF NOT EXISTS comprobante_domicilio_path TEXT,
ADD COLUMN IF NOT EXISTS comprobante_domicilio_url TEXT;
