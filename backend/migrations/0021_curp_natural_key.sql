-- 0021: CURP como llave natural del beneficiario (Issue #32).
--
-- La columna beneficiarios.curp_benef ya existe (text, nullable). Esta migración:
--   1. Añade un CHECK de formato CURP (18 caracteres, estructura oficial).
--   2. Añade UNIQUE(curp_benef) para prevenir beneficiarios duplicados.
--
-- curp_benef se mantiene NULLABLE para permitir borradores incompletos; la CURP
-- es obligatoria sólo al finalizar el estudio (validación en la API). UNIQUE en
-- Postgres permite múltiples NULL, por lo que la unicidad sólo aplica a CURPs reales.
--
-- El folio (beneficiarios.folio + beneficiarios_folio_key) se CONSERVA para los
-- registros legacy; la aplicación deja de generarlo (CURP es el identificador
-- visible). No se elimina nada de forma destructiva.

-- Paso previo OBLIGATORIO: detectar CURPs duplicadas antes de crear el UNIQUE.
-- Si esta consulta devuelve filas, resuelve los duplicados antes de continuar.
SELECT curp_benef, COUNT(*) AS total
FROM beneficiarios
WHERE curp_benef IS NOT NULL
GROUP BY curp_benef
HAVING COUNT(*) > 1;

-- 1. CHECK de formato CURP (sólo se aplica a valores no nulos).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_beneficiarios_curp_formato'
          AND conrelid = 'public.beneficiarios'::regclass
    ) THEN
        ALTER TABLE public.beneficiarios
        ADD CONSTRAINT chk_beneficiarios_curp_formato
        CHECK (
            curp_benef ~ '^[A-Z][AEIOUX][A-Z]{2}\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])[HM](AS|BC|BS|CC|CL|CM|CS|CH|DF|DG|GT|GR|HG|JC|MC|MN|MS|NT|NL|OC|PL|QT|QR|SP|SL|SR|TC|TS|TL|VZ|YN|ZS|NE)[B-DF-HJ-NP-TV-Z]{3}[A-Z\d]\d$'
        );
    END IF;
END $$;

-- 2. UNIQUE(curp_benef) — prevención de duplicados.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_beneficiarios_curp_benef'
          AND conrelid = 'public.beneficiarios'::regclass
    ) THEN
        ALTER TABLE public.beneficiarios
        ADD CONSTRAINT uq_beneficiarios_curp_benef
        UNIQUE (curp_benef);
    END IF;
END $$;
