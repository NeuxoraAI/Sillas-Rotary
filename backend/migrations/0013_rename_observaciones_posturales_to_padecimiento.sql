-- 0013_rename_observaciones_posturales_to_padecimiento.sql
-- Objetivo: Renombrar columna observaciones_posturales a padecimiento en solicitudes_tecnicas
-- El campo ahora almacena una lista de padecimientos seleccionados (checkboxes) en vez de
-- observaciones posturales de texto libre. El nuevo nombre refleja mejor su propósito.

ALTER TABLE public.solicitudes_tecnicas
RENAME COLUMN observaciones_posturales TO padecimiento;
