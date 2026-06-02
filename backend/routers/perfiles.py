"""
Perfiles router — GitHub-style profiles (v2).

Endpoints:
- GET    /api/me/perfil               — Current user profile + stats
- PATCH  /api/me/perfil               — Update current user profile
- GET    /api/me/heatmap              — Contribution heatmap (365 days)
- GET    /api/me/beneficiarios        — User's beneficiaries with edit links
- GET    /api/organizaciones          — List all orgs (admin only)
- POST   /api/organizaciones          — Create org (admin only)
- GET    /api/organizaciones/{id}     — Org detail + stats + heatmap
- PATCH  /api/organizaciones/{id}/lider — Assign leader (admin only)
- GET    /api/organizaciones/{id}/heatmap  — Org aggregate heatmap
- GET    /api/organizaciones/{id}/voluntarios — Org volunteer list
"""

from datetime import date, timedelta, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr

from database import get_db, _DBAdapter
from routers.auth import CurrentUser, require_auth, require_admin, require_roles

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class PerfilUpdateRequest(BaseModel):
    nombre: str | None = None
    email: EmailStr | None = None
    telefono: str | None = None


class OrganizacionCreateRequest(BaseModel):
    nombre: str
    descripcion: str | None = None
    direccion: str | None = None
    telefono: str | None = None
    email: str | None = None
    usuario_id: int | None = None


class LiderAssignRequest(BaseModel):
    lider_usuario_id: int | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user_stats(db: _DBAdapter, usuario_id: int) -> dict:
    """Return {total_capturas, this_month} for a user."""
    total = db.execute(
        "SELECT COUNT(*) AS count FROM estudios_socioeconomicos WHERE usuario_id = %s",
        (usuario_id,),
    ).fetchone()["count"]

    now = datetime.now(timezone.utc)
    this_month = db.execute(
        "SELECT COUNT(*) AS count FROM estudios_socioeconomicos "
        "WHERE usuario_id = %s AND DATE_TRUNC('month', created_at) = DATE_TRUNC('month', %s::timestamptz)",
        (usuario_id, now),
    ).fetchone()["count"]

    return {"total_capturas": total, "this_month": this_month}


def _get_heatmap_data(db: _DBAdapter, usuario_id: int) -> list[dict]:
    """Return [{date: str, count: int}] for last 365 days for a user."""
    rows = db.execute(
        "SELECT DATE(created_at) AS date, COUNT(*) AS count "
        "FROM estudios_socioeconomicos "
        "WHERE usuario_id = %s AND created_at >= NOW() - INTERVAL '1 year' "
        "GROUP BY DATE(created_at) "
        "ORDER BY date",
        (usuario_id,),
    ).fetchall()
    return [{"date": str(r["date"]), "count": r["count"]} for r in rows]


# ---------------------------------------------------------------------------
# Profile endpoints
# ---------------------------------------------------------------------------

@router.get("/me/perfil")
def get_my_perfil(
    db: Annotated[_DBAdapter, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(require_auth)],
) -> dict:
    """Return current user profile with stats."""
    usuario_row = db.execute(
        "SELECT id, nombre, email, telefono, rol FROM usuarios WHERE id = %s",
        (user.usuario_id,),
    ).fetchone()

    stats = _get_user_stats(db, user.usuario_id)
    heatmap = _get_heatmap_data(db, user.usuario_id)

    return {
        "usuario": {
            "id": usuario_row["id"],
            "nombre": usuario_row["nombre"],
            "email": usuario_row["email"],
            "telefono": usuario_row.get("telefono"),
            "rol": usuario_row["rol"],
        },
        "stats": stats,
        "heatmap_data": heatmap,
        "can_edit": True,
    }


@router.patch("/me/perfil")
def patch_my_perfil(
    body: PerfilUpdateRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(require_auth)],
) -> dict:
    """Update current user's profile fields."""
    # Validate nombre if provided
    if body.nombre is not None:
        nombre = body.nombre.strip()
        if len(nombre) < 2 or len(nombre) > 120:
            raise HTTPException(status_code=422, detail="nombre debe tener entre 2 y 120 caracteres")
    else:
        nombre = None

    # Check email uniqueness if changing
    if body.email is not None:
        email = body.email.lower().strip()
        existing = db.execute(
            "SELECT id FROM usuarios WHERE email = %s AND id != %s",
            (email, user.usuario_id),
        ).fetchone()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El email ya está registrado",
            )
    else:
        email = None

    # Build UPDATE SET clause dynamically
    updates = {}
    if nombre is not None:
        updates["nombre"] = nombre
    if email is not None:
        updates["email"] = email
    if body.telefono is not None:
        updates["telefono"] = body.telefono.strip()

    if not updates:
        # Nothing to update, return current profile
        return {"id": user.usuario_id, "nombre": user.nombre, "email": user.email}

    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values())
    values.append(user.usuario_id)

    db.execute(
        f"UPDATE usuarios SET {set_clause} WHERE id = %s",
        values,
    )

    row = db.execute(
        "SELECT id, nombre, email FROM usuarios WHERE id = %s",
        (user.usuario_id,),
    ).fetchone()

    return {"id": row["id"], "nombre": row["nombre"], "email": row["email"]}


@router.get("/me/heatmap")
def get_my_heatmap(
    db: Annotated[_DBAdapter, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(require_auth)],
) -> list[dict]:
    """Return contribution heatmap data for the current user (last 365 days)."""
    return _get_heatmap_data(db, user.usuario_id)


@router.get("/me/beneficiarios")
def get_my_beneficiarios(
    db: Annotated[_DBAdapter, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(require_roles("capturista", "organizacion", "admin"))],
) -> list[dict]:
    """Return beneficiary list with edit links for the current user."""
    rows = db.execute(
        """
        SELECT
            e.id         AS estudio_id,
            b.folio,
            b.nombre     AS beneficiario_nombre,
            b.ciudad,
            e.elaboro_estudio,
            e.fecha_estudio,
            e.status,
            e.created_at
        FROM estudios_socioeconomicos e
        JOIN beneficiarios b ON b.id = e.beneficiario_id
        WHERE e.usuario_id = %s
        ORDER BY e.created_at DESC
        """,
        (user.usuario_id,),
    ).fetchall()

    return [
        {
            "estudio_id": r["estudio_id"],
            "folio": r["folio"],
            "beneficiario_nombre": r["beneficiario_nombre"],
            "ciudad": r["ciudad"],
            "elaboro_estudio": r["elaboro_estudio"],
            "fecha_estudio": str(r["fecha_estudio"]) if r["fecha_estudio"] else None,
            "status": r["status"],
            "edit_url": f"socioeconomico.html?estudio_id={r['estudio_id']}",
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Organization endpoints
# ---------------------------------------------------------------------------

@router.get("/organizaciones")
def list_organizaciones(
    db: Annotated[_DBAdapter, Depends(get_db)],
    _admin: Annotated[CurrentUser, Depends(require_admin)],
) -> list[dict]:
    """List all organizations (admin only)."""
    rows = db.execute(
        """
        SELECT
            o.id,
            o.nombre,
            o.descripcion,
            o.direccion,
            o.telefono,
            o.email,
            o.usuario_id,
            o.lider_usuario_id,
            o.activo,
            o.created_at,
            u.nombre AS lider_nombre
        FROM organizaciones o
        LEFT JOIN usuarios u ON u.id = o.lider_usuario_id
        ORDER BY o.id
        """,
    ).fetchall()

    result = []
    for r in rows:
        org = dict(r)
        # Get total capturas for this org
        if org.get("usuario_id"):
            stats_row = db.execute(
                "SELECT COUNT(*) AS count FROM estudios_socioeconomicos WHERE usuario_id = %s",
                (org["usuario_id"],),
            ).fetchone()
            org["total_capturas"] = stats_row["count"]
        else:
            org["total_capturas"] = 0
        result.append(org)

    return result


@router.post("/organizaciones", status_code=201)
def create_organizacion(
    body: OrganizacionCreateRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    _admin: Annotated[CurrentUser, Depends(require_admin)],
) -> dict:
    """Create a new organization (admin only)."""
    nombre = body.nombre.strip()
    if len(nombre) < 2 or len(nombre) > 200:
        raise HTTPException(status_code=422, detail="nombre debe tener entre 2 y 200 caracteres")

    # Check uniqueness
    existing = db.execute(
        "SELECT id FROM organizaciones WHERE nombre = %s", (nombre,),
    ).fetchone()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Ya existe una organización con ese nombre")

    # Verify usuario_id if provided
    if body.usuario_id is not None:
        user_row = db.execute(
            "SELECT id, activo FROM usuarios WHERE id = %s",
            (body.usuario_id,),
        ).fetchone()
        if user_row is None or not user_row["activo"]:
            raise HTTPException(status_code=400, detail="Usuario no encontrado o inactivo")

    row = db.execute(
        """
        INSERT INTO organizaciones (nombre, descripcion, direccion, telefono, email, usuario_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, nombre
        """,
        (
            nombre,
            body.descripcion.strip() if body.descripcion else None,
            body.direccion.strip() if body.direccion else None,
            body.telefono.strip() if body.telefono else None,
            body.email.strip() if body.email else None,
            body.usuario_id,
        ),
    ).fetchone()

    return {"id": row["id"], "nombre": row["nombre"]}


@router.get("/organizaciones/{org_id}")
def get_organizacion(
    org_id: int,
    db: Annotated[_DBAdapter, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(require_auth)],
) -> dict:
    """Return organization detail with stats and heatmap data."""
    org = db.execute(
        """
        SELECT
            o.id,
            o.nombre,
            o.descripcion,
            o.direccion,
            o.telefono,
            o.email,
            o.usuario_id,
            o.lider_usuario_id,
            o.activo,
            u.nombre AS lider_nombre
        FROM organizaciones o
        LEFT JOIN usuarios u ON u.id = o.lider_usuario_id
        WHERE o.id = %s
        """,
        (org_id,),
    ).fetchone()

    if org is None:
        raise HTTPException(status_code=404, detail="Organización no encontrada")

    result = dict(org)

    # Get stats and heatmap for the org's usuario_id
    if org["usuario_id"]:
        result["stats"] = _get_user_stats(db, org["usuario_id"])
        result["heatmap_data"] = _get_heatmap_data(db, org["usuario_id"])
    else:
        result["stats"] = {"total_capturas": 0, "this_month": 0}
        result["heatmap_data"] = []

    return result


@router.patch("/organizaciones/{org_id}/lider")
def assign_org_lider(
    org_id: int,
    body: LiderAssignRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    _admin: Annotated[CurrentUser, Depends(require_admin)],
) -> dict:
    """Assign or unassign an organization leader (admin only)."""
    org = db.execute(
        "SELECT id FROM organizaciones WHERE id = %s",
        (org_id,),
    ).fetchone()
    if org is None:
        raise HTTPException(status_code=404, detail="Organización no encontrada")

    if body.lider_usuario_id is not None:
        # Verify user exists and is active
        user = db.execute(
            "SELECT id, activo FROM usuarios WHERE id = %s",
            (body.lider_usuario_id,),
        ).fetchone()
        if user is None or not user["activo"]:
            raise HTTPException(status_code=400, detail="Usuario no encontrado o inactivo")

        # Check user is not already a leader of another org
        existing_leader = db.execute(
            "SELECT id FROM organizaciones WHERE lider_usuario_id = %s AND id != %s",
            (body.lider_usuario_id, org_id),
        ).fetchone()
        if existing_leader is not None:
            raise HTTPException(status_code=400, detail="El usuario ya es líder de otra organización")

    db.execute(
        "UPDATE organizaciones SET lider_usuario_id = %s, updated_at = NOW() WHERE id = %s",
        (body.lider_usuario_id, org_id),
    )

    return {"id": org_id, "lider_usuario_id": body.lider_usuario_id}


@router.get("/organizaciones/{org_id}/heatmap")
def get_org_heatmap(
    org_id: int,
    db: Annotated[_DBAdapter, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(require_auth)],
) -> list[dict]:
    """Return aggregate heatmap data for an organization."""
    org = db.execute(
        "SELECT usuario_id FROM organizaciones WHERE id = %s",
        (org_id,),
    ).fetchone()
    if org is None:
        raise HTTPException(status_code=404, detail="Organización no encontrada")
    if org["usuario_id"] is None:
        return []
    return _get_heatmap_data(db, org["usuario_id"])


@router.get("/organizaciones/{org_id}/voluntarios")
def get_org_voluntarios(
    org_id: int,
    db: Annotated[_DBAdapter, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(require_auth)],
) -> list[dict]:
    """Return volunteer list with capture counts for an organization."""
    org = db.execute(
        "SELECT usuario_id FROM organizaciones WHERE id = %s",
        (org_id,),
    ).fetchone()
    if org is None:
        raise HTTPException(status_code=404, detail="Organización no encontrada")
    if org["usuario_id"] is None:
        return []

    rows = db.execute(
        """
        SELECT elaboro_estudio, COUNT(*) AS capturas
        FROM estudios_socioeconomicos
        WHERE usuario_id = %s
        GROUP BY elaboro_estudio
        ORDER BY capturas DESC
        """,
        (org["usuario_id"],),
    ).fetchall()

    return [{"elaboro_estudio": r["elaboro_estudio"], "capturas": r["capturas"]} for r in rows]
