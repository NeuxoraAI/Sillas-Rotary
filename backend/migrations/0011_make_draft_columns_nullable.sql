-- 0011_make_draft_columns_nullable.sql
-- Objetivo: Permitir NULL en campos obligatorios para soportar borradores parciales.
-- Las validaciones de completitud se mantienen en el endpoint /api/finalizar-registro.

-- ── beneficiarios ──
ALTER TABLE public.beneficiarios
ALTER COLUMN nombre DROP NOT NULL;

ALTER TABLE public.beneficiarios
ALTER COLUMN nombres DROP NOT NULL;

ALTER TABLE public.beneficiarios
ALTER COLUMN apellido_paterno DROP NOT NULL;

ALTER TABLE public.beneficiarios
ALTER COLUMN apellido_materno DROP NOT NULL;

ALTER TABLE public.beneficiarios
ALTER COLUMN fecha_nacimiento DROP NOT NULL;

ALTER TABLE public.beneficiarios
ALTER COLUMN diagnostico DROP NOT NULL;

ALTER TABLE public.beneficiarios
ALTER COLUMN calle DROP NOT NULL;

ALTER TABLE public.beneficiarios
ALTER COLUMN colonia DROP NOT NULL;

ALTER TABLE public.beneficiarios
ALTER COLUMN ciudad DROP NOT NULL;

ALTER TABLE public.beneficiarios
ALTER COLUMN telefonos DROP NOT NULL;

-- ── tutores ──
ALTER TABLE public.tutores
ALTER COLUMN nombre DROP NOT NULL;

-- ── estudios_socioeconomicos ──
ALTER TABLE public.estudios_socioeconomicos
ALTER COLUMN elaboro_estudio DROP NOT NULL;

ALTER TABLE public.estudios_socioeconomicos
ALTER COLUMN fecha_estudio DROP NOT NULL;

ALTER TABLE public.estudios_socioeconomicos
ALTER COLUMN sede DROP NOT NULL;

-- ── solicitudes_tecnicas ──
ALTER TABLE public.solicitudes_tecnicas
ALTER COLUMN entorno DROP NOT NULL;

ALTER TABLE public.solicitudes_tecnicas
ALTER COLUMN control_tronco DROP NOT NULL;

ALTER TABLE public.solicitudes_tecnicas
ALTER COLUMN control_cabeza DROP NOT NULL;

ALTER TABLE public.solicitudes_tecnicas
ALTER COLUMN control_de_piernas DROP NOT NULL;
