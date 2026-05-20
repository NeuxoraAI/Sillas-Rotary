-- Migration 0007: Convert 7 medida columns from REAL to NUMERIC(7,3)
-- PRD-Ajustes-Tecnica: Technical measurements now use DECIMAL precision
-- Supports values from 0 to 9999.999 with 3 decimal places.
-- Run against Supabase directly: Supabase SQL editor or local psql

-- 1. Drop existing CHECK constraints on the 7 medida columns
--    (Handle both inline-unnamed and explicitly-named constraints)
DO $$
DECLARE
    con RECORD;
    _cols TEXT[] := ARRAY[
        'altura_total_in',
        'peso_kg',
        'medida_cabeza_asiento',
        'medida_hombro_asiento',
        'medida_prof_asiento',
        'medida_rodilla_talon',
        'medida_ancho_cadera'
    ];
    _col TEXT;
BEGIN
    FOREACH _col IN ARRAY _cols LOOP
        FOR con IN
            SELECT conname
            FROM pg_constraint
            WHERE conrelid = 'solicitudes_tecnicas'::regclass
              AND contype = 'c'
              AND conname LIKE '%' || _col || '%'
        LOOP
            EXECUTE format('ALTER TABLE solicitudes_tecnicas DROP CONSTRAINT IF EXISTS %I', con.conname);
        END LOOP;
    END LOOP;
END $$;

-- 2. Drop any remaining unnamed/default-named CHECKs that the loop missed
ALTER TABLE solicitudes_tecnicas DROP CONSTRAINT IF EXISTS solicitudes_tecnicas_altura_total_in_check;
ALTER TABLE solicitudes_tecnicas DROP CONSTRAINT IF EXISTS solicitudes_tecnicas_peso_kg_check;
ALTER TABLE solicitudes_tecnicas DROP CONSTRAINT IF EXISTS solicitudes_tecnicas_medida_cabeza_asiento_check;
ALTER TABLE solicitudes_tecnicas DROP CONSTRAINT IF EXISTS solicitudes_tecnicas_medida_hombro_asiento_check;
ALTER TABLE solicitudes_tecnicas DROP CONSTRAINT IF EXISTS solicitudes_tecnicas_medida_prof_asiento_check;
ALTER TABLE solicitudes_tecnicas DROP CONSTRAINT IF EXISTS solicitudes_tecnicas_medida_rodilla_talon_check;
ALTER TABLE solicitudes_tecnicas DROP CONSTRAINT IF EXISTS solicitudes_tecnicas_medida_ancho_cadera_check;

-- 3. Alter column types from REAL to NUMERIC(7,3)
ALTER TABLE solicitudes_tecnicas
    ALTER COLUMN altura_total_in      TYPE NUMERIC(7,3),
    ALTER COLUMN peso_kg              TYPE NUMERIC(7,3),
    ALTER COLUMN medida_cabeza_asiento TYPE NUMERIC(7,3),
    ALTER COLUMN medida_hombro_asiento TYPE NUMERIC(7,3),
    ALTER COLUMN medida_prof_asiento  TYPE NUMERIC(7,3),
    ALTER COLUMN medida_rodilla_talon TYPE NUMERIC(7,3),
    ALTER COLUMN medida_ancho_cadera  TYPE NUMERIC(7,3);

-- 4. Add new CHECK constraints (>= 0 AND <= 9999.999)
ALTER TABLE solicitudes_tecnicas
    ADD CONSTRAINT chk_altura_total_in      CHECK (altura_total_in      IS NULL OR (altura_total_in      >= 0 AND altura_total_in      <= 9999.999)),
    ADD CONSTRAINT chk_peso_kg              CHECK (peso_kg              IS NULL OR (peso_kg              >= 0 AND peso_kg              <= 9999.999)),
    ADD CONSTRAINT chk_medida_cabeza_asiento CHECK (medida_cabeza_asiento IS NULL OR (medida_cabeza_asiento >= 0 AND medida_cabeza_asiento <= 9999.999)),
    ADD CONSTRAINT chk_medida_hombro_asiento CHECK (medida_hombro_asiento IS NULL OR (medida_hombro_asiento >= 0 AND medida_hombro_asiento <= 9999.999)),
    ADD CONSTRAINT chk_medida_prof_asiento   CHECK (medida_prof_asiento   IS NULL OR (medida_prof_asiento   >= 0 AND medida_prof_asiento   <= 9999.999)),
    ADD CONSTRAINT chk_medida_rodilla_talon  CHECK (medida_rodilla_talon  IS NULL OR (medida_rodilla_talon  >= 0 AND medida_rodilla_talon  <= 9999.999)),
    ADD CONSTRAINT chk_medida_ancho_cadera   CHECK (medida_ancho_cadera   IS NULL OR (medida_ancho_cadera   >= 0 AND medida_ancho_cadera   <= 9999.999));
