"""
Finalizar Registro router — borradores-v2.

Provides POST /api/finalizar-registro — an atomic endpoint that validates
completeness of all three registration forms (socioeconomico, tecnica, gestion)
and transitions both estudio and solicitud from 'borrador' to 'completo'
in a single database transaction.
"""

from datetime import datetime, timezone
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from pydantic import BaseModel, field_validator

from database import get_db, _DBAdapter
from routers.auth import CurrentUser, assert_resource_owner, require_roles

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class FinalizarRegistroRequest(BaseModel):
    """Request body for POST /api/finalizar-registro."""
    estudio_id: int
    solicitud_id: int

    @field_validator("estudio_id", "solicitud_id")
    @classmethod
    def _must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("debe ser un entero positivo")
        return v


class FinalizarRegistroResponse(BaseModel):
    """Response for successful finalization or idempotent retry."""
    estudio_id: int
    solicitud_id: int
    status: str  # 'completo'
    finalizado_at: Optional[str] = None
    already_completed: bool = False


# ---------------------------------------------------------------------------
# Completeness validation helper
# ---------------------------------------------------------------------------

def _mapear_de_db_tutor(valor: int | None) -> str | None:
    """Map DB integer (tiene_imss, tiene_infonavit) to string."""
    if valor is None:
        return None
    return "SI" if valor == 1 else "NO"


def _validate_all_complete(
    estudio_row: dict,
    solicitud_row: dict,
    beneficiario_row: dict,
    tutores_rows: list[dict],
) -> list[dict]:
    """
    Validate that all required fields are present for all three forms
    per VALIDATION_RULES.md. Returns a list of {form, field} dicts
    identifying each missing required field.

    Forms:
      'beneficiario' — nombre, apellido, fecha, direccion, etc.
      'estudio'      — socioeconomico + gestion fields
      'solicitud'    — tecnica measurements
      'tutor1'       — Tutor 1 required fields
    """
    missing: list[dict] = []

    # ── Beneficiario required fields ───────────────────────────────────────
    ben_required = [
        "nombres", "apellido_paterno", "apellido_materno",
        "curp_benef",
        "fecha_nacimiento", "diagnostico",
        "calle", "colonia", "ciudad", "estado_codigo",
        "sexo", "telefonos",
    ]
    for field in ben_required:
        if not beneficiario_row.get(field):
            missing.append({"form": "beneficiario", "field": field})

    # ── Estudio required fields ────────────────────────────────────────────
    if not estudio_row.get("fecha_estudio"):
        missing.append({"form": "estudio", "field": "fecha_estudio"})

    tuvo = estudio_row.get("tuvo_silla_previa")
    if tuvo is None:
        missing.append({"form": "estudio", "field": "tuvo_silla_previa"})
    elif tuvo == 1 and not estudio_row.get("como_obtuvo_silla"):
        missing.append({"form": "estudio", "field": "como_obtuvo_silla"})

    if not estudio_row.get("elaboro_estudio"):
        missing.append({"form": "estudio", "field": "elaboro_estudio"})

    if not estudio_row.get("sede"):
        missing.append({"form": "estudio", "field": "sede"})

    if not estudio_row.get("ciudad_registro"):
        missing.append({"form": "estudio", "field": "ciudad_registro"})

    # entidad_solicitante and prioridad are from gestion form,
    # stored in solicitud row
    if not solicitud_row.get("entidad_solicitante"):
        missing.append({"form": "gestion", "field": "entidad_solicitante"})

    if not solicitud_row.get("prioridad"):
        missing.append({"form": "gestion", "field": "prioridad"})

    # ── Solicitud (tecnica) required fields ─────────────────────────────────
    medida_fields = [
        "altura_total_in", "peso_kg",
        "medida_cabeza_asiento", "medida_hombro_asiento",
        "medida_prof_asiento", "medida_rodilla_talon",
        "medida_ancho_cadera",
    ]
    for field in medida_fields:
        if solicitud_row.get(field) is None:
            missing.append({"form": "solicitud", "field": field})

    tecnica_catalog_fields = ["entorno", "control_tronco", "control_cabeza", "control_de_piernas"]
    for field in tecnica_catalog_fields:
        if not solicitud_row.get(field):
            missing.append({"form": "solicitud", "field": field})

    # ── Tutor 1 required fields ────────────────────────────────────────────
    tutor1 = next((t for t in tutores_rows if t.get("numero_tutor") == 1), None)
    if tutor1 is None:
        missing.append({"form": "tutor1", "field": "numero_tutor"})
    else:
        tutor1_required = [
            ("edad", lambda v: v is None),
            ("nivel_estudios", lambda v: not v),
            ("estado_civil", lambda v: not v),
            ("vivienda", lambda v: not v),
        ]
        for field, check in tutor1_required:
            if check(tutor1.get(field)):
                missing.append({"form": "tutor1", "field": field})

        # imss_estatus and infonavit_estatus from DB int columns
        imss = _mapear_de_db_tutor(tutor1.get("tiene_imss"))
        if not imss:
            missing.append({"form": "tutor1", "field": "imss_estatus"})
        infonavit = _mapear_de_db_tutor(tutor1.get("tiene_infonavit"))
        if not infonavit:
            missing.append({"form": "tutor1", "field": "infonavit_estatus"})

        # Conditional: empleo
        if not tutor1.get("sin_empleo"):
            if not tutor1.get("fuente_empleo"):
                missing.append({"form": "tutor1", "field": "fuente_empleo"})
            if tutor1.get("ingreso_mensual") is None:
                # ingreso_mensual is REAL in DB, could be 0
                missing.append({"form": "tutor1", "field": "ingreso_mensual"})

            # Conditional: antiguedad
            if tutor1.get("antiguedad_aplica"):
                ant = tutor1.get("antiguedad_meses")
                if ant is None:
                    missing.append({"form": "tutor1", "field": "antiguedad_anios"})

        # Conditional: otras fuentes
        if tutor1.get("otras_fuentes_aplica"):
            if not tutor1.get("otras_fuentes_ingreso"):
                missing.append({"form": "tutor1", "field": "otras_fuentes_ingreso"})
            if tutor1.get("monto_otras_fuentes") is None:
                missing.append({"form": "tutor1", "field": "monto_otras_fuentes"})

    return missing


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/finalizar-registro", response_model=FinalizarRegistroResponse)
def finalizar_registro(
    body: FinalizarRegistroRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("capturista", "admin", "organizacion"))],
) -> FinalizarRegistroResponse:
    """
    Validate completeness of all three forms and transition both estudio
    and solicitud from 'borrador' to 'completo' in a single transaction.

    Idempotent: if both records are already 'completo', returns 200
    without modifying anything.
    """
    # 1. Fetch both records
    estudio_row = db.execute(
        "SELECT * FROM estudios_socioeconomicos WHERE id = %s",
        (body.estudio_id,),
    ).fetchone()

    if estudio_row is None:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")

    solicitud_row = db.execute(
        "SELECT * FROM solicitudes_tecnicas WHERE id = %s",
        (body.solicitud_id,),
    ).fetchone()

    if solicitud_row is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    # 2. Ownership check
    assert_resource_owner(estudio_row["usuario_id"], usuario, db=db)
    assert_resource_owner(solicitud_row["usuario_id"], usuario, db=db)

    # 3. Idempotency: if both already completo, return early
    if estudio_row["status"] == "completo" and solicitud_row["status"] == "completo":
        existing_finalizado = estudio_row.get("finalizado_at")
        return FinalizarRegistroResponse(
            estudio_id=body.estudio_id,
            solicitud_id=body.solicitud_id,
            status="completo",
            finalizado_at=existing_finalizado.isoformat() if existing_finalizado else None,
            already_completed=True,
        )

    # 4. Fetch beneficiario and tutores for completeness validation
    beneficiario_row = db.execute(
        "SELECT * FROM beneficiarios WHERE id = %s",
        (estudio_row["beneficiario_id"],),
    ).fetchone()

    if beneficiario_row is None:
        raise HTTPException(status_code=500, detail="Beneficiario no encontrado")

    tutores_rows = db.execute(
        "SELECT * FROM tutores WHERE beneficiario_id = %s ORDER BY numero_tutor",
        (estudio_row["beneficiario_id"],),
    ).fetchall()

    # 5. Validate completeness
    tutores_dicts = [dict(t) for t in tutores_rows]
    missing = _validate_all_complete(
        dict(estudio_row), dict(solicitud_row),
        dict(beneficiario_row), tutores_dicts,
    )

    if missing:
        raise HTTPException(
            status_code=422,
            detail={
                "type": "completeness_error",
                "message": "Faltan campos obligatorios",
                "missing": missing,
            },
        )

    # 6. Update both records in the implicit transaction.
    # On error, the exception propagates and get_db rolls back.
    finalizado_at = datetime.now(timezone.utc)

    db.execute(
        """
        UPDATE estudios_socioeconomicos
        SET status = 'completo', finalizado_at = %s, updated_at = NOW()
        WHERE id = %s
        """,
        (finalizado_at, body.estudio_id),
    )

    db.execute(
        """
        UPDATE solicitudes_tecnicas
        SET status = 'completo', finalizado_at = %s, updated_at = NOW()
        WHERE id = %s
        """,
        (finalizado_at, body.solicitud_id),
    )

    return FinalizarRegistroResponse(
        estudio_id=body.estudio_id,
        solicitud_id=body.solicitud_id,
        status="completo",
        finalizado_at=finalizado_at.isoformat(),
        already_completed=False,
    )
