def test_init_db_contains_procesos_tecnicos_schema_without_organizacion():
    from init_db import DDL

    ddl_text = "\n".join(DDL)
    assert "CREATE TABLE IF NOT EXISTS procesos_tecnicos" in ddl_text
    assert "UNIQUE(beneficiario_id)" in ddl_text
    assert "estado" in ddl_text
    assert "sin_iniciar" in ddl_text
    assert "en_proceso" in ddl_text
    assert "finalizado" in ddl_text
    assert "revision_pendiente" in ddl_text
    assert "organizacion" not in ddl_text


def test_init_db_contains_participantes_append_only_table():
    from init_db import DDL

    ddl_text = "\n".join(DDL)
    assert "CREATE TABLE IF NOT EXISTS procesos_tecnicos_participantes" in ddl_text
    assert "accion" in ddl_text
    assert "inicio" in ddl_text
    assert "continuacion" in ddl_text
    assert "finalizacion" in ddl_text
    assert "revision" in ddl_text


def test_apply_transition_allows_valid_flow():
    from routers.tecnica import apply_tecnico_transition

    assert apply_tecnico_transition("sin_iniciar", "iniciar") == "en_proceso"
    assert apply_tecnico_transition("en_proceso", "continuar") == "en_proceso"
    assert apply_tecnico_transition("en_proceso", "finalizar") == "finalizado"
    assert apply_tecnico_transition("en_proceso", "solicitar_revision") == "revision_pendiente"


def test_apply_transition_rejects_invalid_flow():
    from fastapi import HTTPException
    from routers.tecnica import apply_tecnico_transition

    try:
        apply_tecnico_transition("finalizado", "continuar")
        assert False, "Debió lanzar HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail["type"] == "invalid_transition"


def test_ensure_process_uniqueness_conflict_when_existing_process_present():
    from fastapi import HTTPException
    from routers.tecnica import ensure_single_process_per_beneficiario

    existing = {"id": 99, "beneficiario_id": 10}
    try:
        ensure_single_process_per_beneficiario(existing)
        assert False, "Debió lanzar HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail["type"] == "unique_violation"


def test_merge_participant_ids_preserves_order_and_avoids_duplicates():
    from routers.tecnica import merge_participant_ids

    merged = merge_participant_ids([5, 8], 8)
    assert merged == [5, 8]

    merged = merge_participant_ids([5, 8], 11)
    assert merged == [5, 8, 11]
