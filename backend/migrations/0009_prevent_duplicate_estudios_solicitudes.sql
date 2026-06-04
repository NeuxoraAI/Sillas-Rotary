-- Prevent duplicate socioeconomic studies and technical requests for the same
-- beneficiary captured by the same user. Run the duplicate-detection queries
-- first; if they return rows, merge or remove duplicates before adding constraints.

SELECT beneficiario_id, usuario_id, COUNT(*) AS total
FROM estudios_socioeconomicos
GROUP BY beneficiario_id, usuario_id
HAVING COUNT(*) > 1;

SELECT beneficiario_id, usuario_id, COUNT(*) AS total
FROM solicitudes_tecnicas
GROUP BY beneficiario_id, usuario_id
HAVING COUNT(*) > 1;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_estudio_beneficiario_usuario'
          AND conrelid = 'estudios_socioeconomicos'::regclass
    ) THEN
        ALTER TABLE estudios_socioeconomicos
        ADD CONSTRAINT uq_estudio_beneficiario_usuario
        UNIQUE (beneficiario_id, usuario_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_solicitud_beneficiario_usuario'
          AND conrelid = 'solicitudes_tecnicas'::regclass
    ) THEN
        ALTER TABLE solicitudes_tecnicas
        ADD CONSTRAINT uq_solicitud_beneficiario_usuario
        UNIQUE (beneficiario_id, usuario_id);
    END IF;
END $$;
