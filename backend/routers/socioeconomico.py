from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from database import get_db

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
    sede: str
    status: str = "borrador"

    @field_validator("status")
    @classmethod
    def status_valido(cls, v: str) -> str:
        if v not in ("borrador", "completo"):
            raise ValueError("status debe ser 'borrador' o 'completo'")
        return v


class EstudioCreateRequest(BaseModel):
    capturista_id: int
    beneficiario: BeneficiarioIn
    tutores: list[TutorIn]
    estudio: EstudioIn


class EstudioCreateResponse(BaseModel):
    estudio_id: int
    beneficiario_id: int
    status: str


class EstudioUpdateRequest(BaseModel):
    otras_fuentes_ingreso: Optional[str] = None
    monto_otras_fuentes: Optional[float] = None
    tuvo_silla_previa: Optional[bool] = None
    como_obtuvo_silla: Optional[str] = None
    elaboro_estudio: Optional[str] = None
    fecha_estudio: Optional[str] = None
    sede: Optional[str] = None
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
def crear_estudio(body: EstudioCreateRequest) -> EstudioCreateResponse:
    _validar_tutores(body.tutores)

    with get_db() as conn:
        # 1. INSERT beneficiario
        beneficiario_id = conn.execute(
            """
            INSERT INTO beneficiarios
                (nombre, fecha_nacimiento, diagnostico, calle, colonia, ciudad, telefonos)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
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
            ),
        ).fetchone()["id"]

        # 2. INSERT tutores
        for tutor in body.tutores:
            conn.execute(
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
                    1 if tutor.tiene_imss else 0,
                    1 if tutor.tiene_infonavit else 0,
                ),
            )

        # 3. INSERT estudio
        estudio = body.estudio
        estudio_id = conn.execute(
            """
            INSERT INTO estudios_socioeconomicos
                (beneficiario_id, capturista_id, otras_fuentes_ingreso,
                 monto_otras_fuentes, tuvo_silla_previa, como_obtuvo_silla,
                 elaboro_estudio, fecha_estudio, sede, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                beneficiario_id,
                body.capturista_id,
                estudio.otras_fuentes_ingreso,
                estudio.monto_otras_fuentes,
                1 if estudio.tuvo_silla_previa else 0,
                estudio.como_obtuvo_silla,
                estudio.elaboro_estudio,
                estudio.fecha_estudio,
                estudio.sede,
                estudio.status,
            ),
        ).fetchone()["id"]

    return EstudioCreateResponse(
        estudio_id=estudio_id,
        beneficiario_id=beneficiario_id,
        status=body.estudio.status,
    )


@router.get("/estudios/{id}")
def obtener_estudio(id: int) -> dict:
    with get_db() as conn:
        estudio_row = conn.execute(
            "SELECT * FROM estudios_socioeconomicos WHERE id = %s", (id,)
        ).fetchone()

        if estudio_row is None:
            raise HTTPException(status_code=404, detail="Estudio no encontrado")

        beneficiario_row = conn.execute(
            "SELECT * FROM beneficiarios WHERE id = %s",
            (estudio_row["beneficiario_id"],),
        ).fetchone()

        tutores_rows = conn.execute(
            "SELECT * FROM tutores WHERE beneficiario_id = %s ORDER BY numero_tutor",
            (estudio_row["beneficiario_id"],),
        ).fetchall()

    result = dict(estudio_row)
    result["beneficiario"] = dict(beneficiario_row)
    result["tutores"] = [dict(t) for t in tutores_rows]

    return result


@router.patch("/estudios/{id}", response_model=EstudioUpdateResponse)
def actualizar_estudio(id: int, body: EstudioUpdateRequest) -> EstudioUpdateResponse:
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM estudios_socioeconomicos WHERE id = %s", (id,)
        ).fetchone()

        if existing is None:
            raise HTTPException(status_code=404, detail="Estudio no encontrado")

        fields = body.model_dump(exclude_none=True)
        if not fields:
            row = conn.execute(
                "SELECT id, status, updated_at FROM estudios_socioeconomicos WHERE id = %s",
                (id,),
            ).fetchone()
            return EstudioUpdateResponse(
                estudio_id=row["id"],
                status=row["status"],
                updated_at=row["updated_at"].isoformat(),
            )

        if "tuvo_silla_previa" in fields:
            fields["tuvo_silla_previa"] = 1 if fields["tuvo_silla_previa"] else 0

        set_clause = ", ".join(f"{k} = %s" for k in fields)
        values = list(fields.values())
        values.append(id)

        conn.execute(
            f"UPDATE estudios_socioeconomicos SET {set_clause}, updated_at = NOW() WHERE id = %s",
            values,
        )

        row = conn.execute(
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
