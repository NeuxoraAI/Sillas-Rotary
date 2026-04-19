"""
Estudio socioeconómico router (v2).

Changes from v1:
- Uses Depends(get_db) instead of context manager
- Uses require_auth (JWT) — capturista_id replaced by usuario.usuario_id
- region_id + sede at top level of EstudioCreateRequest (moved from EstudioIn)
- Calls generate_folio() to assign structured folio to each beneficiario
- Returns folio in EstudioCreateResponse
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from database import get_db, _DBAdapter
from routers.auth import CurrentUser, require_auth
from routers.regiones import generate_folio

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class BeneficiarioIn(BaseModel):
    nombre: str
    fecha_nacimiento: str
    diagnostico: str
    calle: str
    colonia: str
    ciudad: str
    telefonos: str
    email: Optional[str] = None


class TutorIn(BaseModel):
    numero_tutor: int
    nombre: str
    edad: Optional[int] = None
    nivel_estudios: Optional[str] = None
    estado_civil: Optional[str] = None
    num_hijos: Optional[int] = None
    vivienda: Optional[str] = None
    fuente_empleo: Optional[str] = None
    antiguedad: Optional[str] = None
    ingreso_mensual: Optional[float] = None
    tiene_imss: bool = False
    tiene_infonavit: bool = False

    @field_validator("numero_tutor")
    @classmethod
    def numero_tutor_valido(cls, v: int) -> int:
        if v not in (1, 2):
            raise ValueError("numero_tutor debe ser 1 o 2")
        return v


class EstudioIn(BaseModel):
    otras_fuentes_ingreso: Optional[str] = None
    monto_otras_fuentes: Optional[float] = None
    tuvo_silla_previa: bool
    como_obtuvo_silla: Optional[str] = None
    elaboro_estudio: str
    fecha_estudio: str
    status: str = "borrador"

    @field_validator("status")
    @classmethod
    def status_valido(cls, v: str) -> str:
        if v not in ("borrador", "completo"):
            raise ValueError("status debe ser 'borrador' o 'completo'")
        return v


class EstudioCreateRequest(BaseModel):
    """
    Top-level request for creating a full estudio socioeconómico.

    Note: region_id and sede are set here (not inside estudio) because they
    describe WHEN and WHERE the registration happens, not the study itself.
    """
    region_id: int
    sede: str
    beneficiario: BeneficiarioIn
    tutores: list[TutorIn]
    estudio: EstudioIn


class EstudioCreateResponse(BaseModel):
    estudio_id: int
    beneficiario_id: int
    folio: str
    status: str


class EstudioUpdateRequest(BaseModel):
    otras_fuentes_ingreso: Optional[str] = None
    monto_otras_fuentes: Optional[float] = None
    tuvo_silla_previa: Optional[bool] = None
    como_obtuvo_silla: Optional[str] = None
    elaboro_estudio: Optional[str] = None
    fecha_estudio: Optional[str] = None
    status: Optional[str] = None

    @field_validator("status")
    @classmethod
    def status_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("borrador", "completo"):
            raise ValueError("status debe ser 'borrador' o 'completo'")
        return v


class EstudioUpdateResponse(BaseModel):
    estudio_id: int
    status: str
    updated_at: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/estudios", status_code=201, response_model=EstudioCreateResponse)
def crear_estudio(
    body: EstudioCreateRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_auth)],
) -> EstudioCreateResponse:
    """Create a complete estudio socioeconómico with beneficiario, tutores, and study data."""
    _validar_tutores(body.tutores)

    # 1. Generate structured folio (atomic counter per region/year)
    folio = generate_folio(db, body.region_id)

    # 2. INSERT beneficiario (with folio + region + sede)
    beneficiario_id = db.execute(
        """
        INSERT INTO beneficiarios
            (nombre, fecha_nacimiento, diagnostico, calle, colonia, ciudad,
             telefonos, email, folio, region_id, sede)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            body.beneficiario.nombre,
            body.beneficiario.fecha_nacimiento,
            body.beneficiario.diagnostico,
            body.beneficiario.calle,
            body.beneficiario.colonia,
            body.beneficiario.ciudad,
            body.beneficiario.telefonos,
            body.beneficiario.email,
            folio,
            body.region_id,
            body.sede,
        ),
    ).fetchone()["id"]

    # 3. INSERT tutores
    for tutor in body.tutores:
        db.execute(
            """
            INSERT INTO tutores
                (beneficiario_id, numero_tutor, nombre, edad, nivel_estudios,
                 estado_civil, num_hijos, vivienda, fuente_empleo, antiguedad,
                 ingreso_mensual, tiene_imss, tiene_infonavit)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                beneficiario_id,
                tutor.numero_tutor,
                tutor.nombre,
                tutor.edad,
                tutor.nivel_estudios or None,
                tutor.estado_civil or None,
                tutor.num_hijos if tutor.num_hijos is not None else 0,
                tutor.vivienda or None,
                tutor.fuente_empleo or None,
                tutor.antiguedad or None,
                tutor.ingreso_mensual,
                tutor.tiene_imss,
                tutor.tiene_infonavit,
            ),
        )

    # 4. INSERT estudio (now uses usuario_id instead of capturista_id)
    estudio = body.estudio
    estudio_id = db.execute(
        """
        INSERT INTO estudios_socioeconomicos
            (beneficiario_id, usuario_id, otras_fuentes_ingreso,
             monto_otras_fuentes, tuvo_silla_previa, como_obtuvo_silla,
             elaboro_estudio, fecha_estudio, sede, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            beneficiario_id,
            usuario.usuario_id,
            estudio.otras_fuentes_ingreso,
            estudio.monto_otras_fuentes,
            estudio.tuvo_silla_previa,
            estudio.como_obtuvo_silla,
            estudio.elaboro_estudio,
            estudio.fecha_estudio,
            body.sede,
            estudio.status,
        ),
    ).fetchone()["id"]

    return EstudioCreateResponse(
        estudio_id=estudio_id,
        beneficiario_id=beneficiario_id,
        folio=folio,
        status=estudio.status,
    )


@router.get("/estudios/{id}")
def obtener_estudio(
    id: int,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_auth)],
) -> dict:
    """Retrieve a full estudio by ID. Only the owner or an admin may read it."""
    estudio_row = db.execute(
        "SELECT * FROM estudios_socioeconomicos WHERE id = %s", (id,)
    ).fetchone()

    if estudio_row is None:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")

    if usuario.rol != "admin" and estudio_row["usuario_id"] != usuario.usuario_id:
        raise HTTPException(status_code=403, detail="No tiene acceso a este estudio")

    beneficiario_row = db.execute(
        "SELECT * FROM beneficiarios WHERE id = %s",
        (estudio_row["beneficiario_id"],),
    ).fetchone()

    tutores_rows = db.execute(
        "SELECT * FROM tutores WHERE beneficiario_id = %s ORDER BY numero_tutor",
        (estudio_row["beneficiario_id"],),
    ).fetchall()

    result = dict(estudio_row)
    result["beneficiario"] = dict(beneficiario_row)
    result["tutores"] = [dict(t) for t in tutores_rows]

    return result


@router.patch("/estudios/{id}", response_model=EstudioUpdateResponse)
def actualizar_estudio(
    id: int,
    body: EstudioUpdateRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_auth)],
) -> EstudioUpdateResponse:
    """Partial update of an estudio. Only the owner or an admin may update it."""
    existing = db.execute(
        "SELECT id, usuario_id FROM estudios_socioeconomicos WHERE id = %s", (id,)
    ).fetchone()

    if existing is None:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")

    if usuario.rol != "admin" and existing["usuario_id"] != usuario.usuario_id:
        raise HTTPException(status_code=403, detail="No tiene acceso a este estudio")

    fields = body.model_dump(exclude_none=True)
    if not fields:
        row = db.execute(
            "SELECT id, status, updated_at FROM estudios_socioeconomicos WHERE id = %s",
            (id,),
        ).fetchone()
        return EstudioUpdateResponse(
            estudio_id=row["id"],
            status=row["status"],
            updated_at=row["updated_at"].isoformat(),
        )

    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values())
    values.append(id)

    db.execute(
        f"UPDATE estudios_socioeconomicos SET {set_clause}, updated_at = NOW() WHERE id = %s",
        values,
    )

    row = db.execute(
        "SELECT id, status, updated_at FROM estudios_socioeconomicos WHERE id = %s",
        (id,),
    ).fetchone()

    return EstudioUpdateResponse(
        estudio_id=row["id"],
        status=row["status"],
        updated_at=row["updated_at"].isoformat(),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validar_tutores(tutores: list[TutorIn]) -> None:
    if not tutores:
        raise HTTPException(status_code=400, detail="Se requiere al menos un tutor")
    numeros = [t.numero_tutor for t in tutores]
    if len(numeros) != len(set(numeros)):
        raise HTTPException(status_code=400, detail="No se pueden repetir los números de tutor")
    for num in numeros:
        if num not in (1, 2):
            raise HTTPException(status_code=400, detail=f"numero_tutor inválido: {num}")
