-- 0015_prd_opcion_b_fields.sql

ALTER TABLE public.beneficiarios
ADD COLUMN IF NOT EXISTS num_ext TEXT,
ADD COLUMN IF NOT EXISTS num_int TEXT,
ADD COLUMN IF NOT EXISTS estado_codigo TEXT,
ADD COLUMN IF NOT EXISTS estado_nombre TEXT,
ADD COLUMN IF NOT EXISTS sexo TEXT;

ALTER TABLE public.tutores
ADD COLUMN IF NOT EXISTS antiguedad_meses INTEGER,
ADD COLUMN IF NOT EXISTS antiguedad_aplica INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS sin_empleo INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS otras_fuentes_aplica INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS otras_fuentes_ingreso TEXT,
ADD COLUMN IF NOT EXISTS monto_otras_fuentes REAL;

ALTER TABLE public.estudios_socioeconomicos
ADD COLUMN IF NOT EXISTS ciudad_registro TEXT;

ALTER TABLE public.solicitudes_tecnicas
ADD COLUMN IF NOT EXISTS unidad_captura TEXT DEFAULT 'in';
