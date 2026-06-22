-- Migration 0016: Add unidad_peso_captura column to solicitudes_tecnicas
-- Feature: Unidades de Peso y Zoom de Imagen
-- Field technicians can now record weight in pounds (lb) or kilograms (kg).
-- The DB always stores the canonical kg value; unidad_peso_captura records
-- which unit the technician originally entered.

-- 1. Add column with DEFAULT 'kg' and CHECK constraint
ALTER TABLE solicitudes_tecnicas
ADD COLUMN unidad_peso_captura TEXT NOT NULL DEFAULT 'kg'
CHECK (unidad_peso_captura IN ('kg', 'lb'));

-- 2. Backfill existing rows — they were all captured in kg
UPDATE solicitudes_tecnicas SET unidad_peso_captura = 'kg' WHERE unidad_peso_captura IS NULL;

-- Rollback:
-- ALTER TABLE solicitudes_tecnicas DROP COLUMN unidad_peso_captura;
