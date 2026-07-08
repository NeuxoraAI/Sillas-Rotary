-- 0030_tutores_nombre_estructurado.sql
-- Issue #161 (QA de borradores): el nombre del tutor se guardaba SOLO como
-- `nombre` compuesto (concatenación de nombres + apellidos), por lo que al
-- reanudar un borrador el frontend tenía que adivinar la división con una
-- heurística (draft-store.js) que falla con apellidos compuestos o nombres
-- de 2 palabras. Se agregan las columnas estructuradas — espejo de lo que
-- 0005_prd_ajustes_nombre_estructurado hizo para `beneficiarios`.
--
-- `nombre` compuesto se conserva (dual-write en la API): lo consumen el
-- export de admin (tutor_nombre) y las filas legacy. Filas existentes
-- quedan con NULL en las columnas nuevas; el frontend mantiene la heurística
-- como fallback de lectura y se autocorrigen al siguiente guardado.

ALTER TABLE public.tutores
    ADD COLUMN IF NOT EXISTS nombres TEXT NULL,
    ADD COLUMN IF NOT EXISTS apellido_paterno TEXT NULL,
    ADD COLUMN IF NOT EXISTS apellido_materno TEXT NULL;
