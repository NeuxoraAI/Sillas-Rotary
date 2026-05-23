-- Migration: Add tiempo_diagnostico fields and telefono_alternativo to beneficiarios
-- 0009_add_tiempo_diagnostico_and_telefono_alternativo.sql

ALTER TABLE beneficiarios
  ADD COLUMN IF NOT EXISTS tiempo_diagnostico_anios INTEGER
    CHECK (tiempo_diagnostico_anios IS NULL OR (tiempo_diagnostico_anios >= 0 AND tiempo_diagnostico_anios <= 120)),
  ADD COLUMN IF NOT EXISTS tiempo_diagnostico_meses INTEGER
    CHECK (tiempo_diagnostico_meses IS NULL OR (tiempo_diagnostico_meses >= 0 AND tiempo_diagnostico_meses <= 11)),
  ADD COLUMN IF NOT EXISTS telefono_alternativo TEXT;
