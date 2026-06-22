-- 0018_add_soporte_oxigeno_to_solicitudes_tecnicas.sql

ALTER TABLE public.solicitudes_tecnicas
ADD COLUMN IF NOT EXISTS soporte_oxigeno BOOLEAN NOT NULL DEFAULT FALSE;
