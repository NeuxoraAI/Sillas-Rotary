ALTER TABLE public.solicitudes_tecnicas
ADD COLUMN IF NOT EXISTS soporte_oxigeno BOOLEAN NOT NULL DEFAULT FALSE;
