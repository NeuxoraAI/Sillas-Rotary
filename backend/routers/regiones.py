"""
Region catalog router (v2).

Endpoints:
- POST GET /api/paises          — Country CRUD (admin)
- POST GET /api/regiones        — Region CRUD (admin)

Also exports generate_folio(db, region_id) for use in socioeconomico router.
"""

import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator

from database import get_db, _DBAdapter
from routers.auth import CurrentUser, require_admin, require_auth
from utils.folio import format_folio

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class PaisCreateRequest(BaseModel):
    nombre: str
    codigo: str

    @field_validator("codigo")
    @classmethod
    def codigo_uppercase(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("nombre")
    @classmethod
    def nombre_strip(cls, v: str) -> str:
        return v.strip()


class PaisResponse(BaseModel):
    pais_id: int
    nombre: str
    codigo: str
    activo: bool


class RegionCreateRequest(BaseModel):
    pais_id: int
    nombre: str
    codigo: str

    @field_validator("codigo")
    @classmethod
    def codigo_uppercase(cls, v: str) -> str:
        v = v.strip().upper()
        if len(v) < 2 or len(v) > 5:
            raise ValueError("El código debe tener entre 2 y 5 caracteres")
        return v

    @field_validator("nombre")
    @classmethod
    def nombre_strip(cls, v: str) -> str:
        return v.strip()


class RegionResponse(BaseModel):
    region_id: int
    pais_id: int
    nombre: str
    codigo: str
    activo: bool


# ---------------------------------------------------------------------------
# Folio generation (exported for use in socioeconomico router)
# ---------------------------------------------------------------------------

def generate_folio(db: _DBAdapter, region_id: int) -> str:
    """
    Generate the next folio for the given region and current year.

    Uses a single atomic INSERT ... ON CONFLICT DO UPDATE to safely
    increment the counter without race conditions.

    Args:
        db: Active database adapter
        region_id: ID of the region for which to generate the folio

    Returns:
        Formatted folio string like "MX-LON-2026-001"

    Raises:
        HTTPException 404 if region_id is invalid
    """
    # Fetch region + pais codes
    row = db.execute(
        """
        SELECT r.codigo AS region_codigo, p.codigo AS pais_codigo
        FROM regiones r
        JOIN paises p ON p.id = r.pais_id
        WHERE r.id = %s AND r.activo = TRUE
        """,
        (region_id,),
    ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Región no encontrada o inactiva: {region_id}",
        )

    pais_codigo = row["pais_codigo"]
    region_codigo = row["region_codigo"]
    anio = datetime.date.today().year

    # Atomic counter upsert — race-safe
    counter_row = db.execute(
        """
        INSERT INTO region_counters (pais_codigo, region_codigo, anio, ultimo_numero)
        VALUES (%s, %s, %s, 1)
        ON CONFLICT (pais_codigo, region_codigo, anio)
        DO UPDATE SET ultimo_numero = region_counters.ultimo_numero + 1
        RETURNING ultimo_numero
        """,
        (pais_codigo, region_codigo, anio),
    ).fetchone()

    numero = counter_row["ultimo_numero"]
    return format_folio(pais_codigo, region_codigo, anio, numero)


# ---------------------------------------------------------------------------
# Países endpoints
# ---------------------------------------------------------------------------

@router.post("/paises", status_code=status.HTTP_201_CREATED, response_model=PaisResponse)
def create_pais(
    body: PaisCreateRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    _admin: Annotated[CurrentUser, Depends(require_admin)],
) -> PaisResponse:
    """Create a new country. Admin only."""
    existing = db.execute(
        "SELECT id FROM paises WHERE codigo = %s",
        (body.codigo,),
    ).fetchone()

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El código de país '{body.codigo}' ya existe",
        )

    row = db.execute(
        "INSERT INTO paises (nombre, codigo) VALUES (%s, %s) RETURNING id, nombre, codigo, activo",
        (body.nombre, body.codigo),
    ).fetchone()

    return PaisResponse(
        pais_id=row["id"],
        nombre=row["nombre"],
        codigo=row["codigo"],
        activo=row["activo"],
    )


@router.get("/paises", response_model=list[PaisResponse])
def list_paises(
    db: Annotated[_DBAdapter, Depends(get_db)],
    _user: Annotated[CurrentUser, Depends(require_auth)],
) -> list[PaisResponse]:
    """List all active countries. Any authenticated user."""
    rows = db.execute(
        "SELECT id, nombre, codigo, activo FROM paises WHERE activo = TRUE ORDER BY nombre"
    ).fetchall()

    return [
        PaisResponse(pais_id=r["id"], nombre=r["nombre"], codigo=r["codigo"], activo=r["activo"])
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Regiones endpoints
# ---------------------------------------------------------------------------

@router.post("/regiones", status_code=status.HTTP_201_CREATED, response_model=RegionResponse)
def create_region(
    body: RegionCreateRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    _admin: Annotated[CurrentUser, Depends(require_admin)],
) -> RegionResponse:
    """Create a new region within a country. Admin only."""
    # Check pais exists
    pais = db.execute("SELECT id FROM paises WHERE id = %s", (body.pais_id,)).fetchone()
    if pais is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"País no encontrado: {body.pais_id}",
        )

    # Check unique codigo within pais
    existing = db.execute(
        "SELECT id FROM regiones WHERE pais_id = %s AND codigo = %s",
        (body.pais_id, body.codigo),
    ).fetchone()

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El código '{body.codigo}' ya existe para este país",
        )

    row = db.execute(
        """
        INSERT INTO regiones (pais_id, nombre, codigo)
        VALUES (%s, %s, %s)
        RETURNING id, pais_id, nombre, codigo, activo
        """,
        (body.pais_id, body.nombre, body.codigo),
    ).fetchone()

    return RegionResponse(
        region_id=row["id"],
        pais_id=row["pais_id"],
        nombre=row["nombre"],
        codigo=row["codigo"],
        activo=row["activo"],
    )


@router.get("/regiones", response_model=list[RegionResponse])
def list_regiones(
    db: Annotated[_DBAdapter, Depends(get_db)],
    _user: Annotated[CurrentUser, Depends(require_auth)],
    pais_id: Optional[int] = Query(default=None, description="Filter by country ID"),
) -> list[RegionResponse]:
    """List active regions. Any authenticated user. Optionally filtered by pais_id."""
    if pais_id is not None:
        rows = db.execute(
            """
            SELECT id, pais_id, nombre, codigo, activo
            FROM regiones
            WHERE pais_id = %s AND activo = TRUE
            ORDER BY nombre
            """,
            (pais_id,),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT id, pais_id, nombre, codigo, activo FROM regiones WHERE activo = TRUE ORDER BY nombre"
        ).fetchall()

    return [
        RegionResponse(
            region_id=r["id"],
            pais_id=r["pais_id"],
            nombre=r["nombre"],
            codigo=r["codigo"],
            activo=r["activo"],
        )
        for r in rows
    ]
