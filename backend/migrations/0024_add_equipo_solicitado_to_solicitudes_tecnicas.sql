-- 0024_add_equipo_solicitado_to_solicitudes_tecnicas.sql

ALTER TABLE public.solicitudes_tecnicas
ADD COLUMN IF NOT EXISTS equipo_solicitado TEXT;
