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
- PATCH  /api/organizaciones/{id}     — Update org details (admin only)
- POST   /api/organizaciones/{id}/lider — Add leader (admin only)
- DELETE /api/organizaciones/{id}/lider/{usuario_id} — Remove leader (admin only)
- POST   /api/organizaciones/{id}/miembros — Add member (admin only)
- DELETE /api/organizaciones/{id}/miembros/{usuario_id} — Remove member (admin only)
- GET    /api/organizaciones/{id}/heatmap  — Org aggregate heatmap
- GET    /api/organizaciones/{id}/voluntarios — Org volunteer list
"""

from datetime import date, timedelta, datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr

from database import get_db, _DBAdapter
from routers.auth import CurrentUser, require_auth, require_admin, require_roles, _hash_password

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
    email: str | None = None
    password: str | None = None
    usuario_id: int | None = None
    descripcion: str | None = None
    direccion: str | None = None
    telefono: str | None = None


class LiderAssignRequest(BaseModel):
    lider_usuario_id: int | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user_stats(db: _DBAdapter, usuario_id: int) -> dict:
    """Return {total_capturas, this_month, pendientes} for a user."""
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

    pendientes = db.execute(
        "SELECT COUNT(*) AS count FROM estudios_socioeconomicos "
        "WHERE usuario_id = %s AND status = 'borrador'",
        (usuario_id,),
    ).fetchone()["count"]

    return {"total_capturas": total, "this_month": this_month, "pendientes": pendientes}


def _get_heatmap_data(db: _DBAdapter, usuario_id: int, year: int | None = None) -> list[dict]:
    """Return [{date: str, count: int}] for a user's activity.

    Args:
        year: Optional calendar year to filter by. Defaults to last 365 days
              if not provided (backward-compatible).
    """
    if year is not None:
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        next_start = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        rows = db.execute(
            "SELECT DATE(created_at) AS date, COUNT(*) AS count "
            "FROM estudios_socioeconomicos "
            "WHERE usuario_id = %s AND created_at >= %s AND created_at < %s "
            "GROUP BY DATE(created_at) "
            "ORDER BY date",
            (usuario_id, start, next_start),
        ).fetchall()
    else:
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
    """Return current user profile with stats and org leadership info."""
    usuario_row = db.execute(
        "SELECT id, nombre, email, telefono, rol, avatar_url FROM usuarios WHERE id = %s",
        (user.usuario_id,),
    ).fetchone()

    stats = _get_user_stats(db, user.usuario_id)

    # Get last activity date (most recent created or resumed/updated estudio)
    last_activity_row = db.execute(
        "SELECT MAX(GREATEST(created_at, updated_at)) AS last_activity_date "
        "FROM estudios_socioeconomicos WHERE usuario_id = %s",
        (user.usuario_id,),
    ).fetchone()
    last_activity_date = last_activity_row["last_activity_date"]
    if last_activity_date is not None:
        last_activity_date = last_activity_date.isoformat()

    # Check orgs the user leads (via organizaciones_lideres)
    leader_rows = db.execute(
        """
        SELECT o.id, o.nombre, o.descripcion, o.direccion, o.telefono, o.email
        FROM organizaciones o
        JOIN organizaciones_lideres ol ON ol.organizacion_id = o.id
        WHERE ol.usuario_id = %s AND o.activo = TRUE
        """,
        (user.usuario_id,),
    ).fetchall()

    # Check orgs the user is a member of (via organizaciones_miembros)
    member_rows = db.execute(
        """
        SELECT o.id, o.nombre, o.descripcion, o.direccion, o.telefono, o.email
        FROM organizaciones o
        JOIN organizaciones_miembros om ON om.organizacion_id = o.id
        WHERE om.usuario_id = %s AND o.activo = TRUE
        """,
        (user.usuario_id,),
    ).fetchall()

    return {
        "usuario": {
            "id": usuario_row["id"],
            "nombre": usuario_row["nombre"],
            "email": usuario_row["email"],
            "telefono": usuario_row.get("telefono"),
            "rol": usuario_row["rol"],
            "avatar_url": usuario_row.get("avatar_url"),
        },
        "stats": stats,
        "last_activity_date": last_activity_date,
        "heatmap_data": _get_heatmap_data(db, user.usuario_id),
        "organizaciones_lider": [dict(r) for r in leader_rows],
        "organizaciones_miembro": [dict(r) for r in member_rows],
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
    year: Annotated[int | None, Query(description="Calendar year to filter heatmap data")] = None,
    db: Annotated[_DBAdapter, Depends(get_db)] = None,
    user: Annotated[CurrentUser, Depends(require_auth)] = None,
) -> list[dict]:
    """Return contribution heatmap data for the current user.

    Args:
        year: Optional calendar year (e.g. 2025). If omitted, returns last 365 days.
    """
    return _get_heatmap_data(db, user.usuario_id, year=year)


@router.get("/me/beneficiarios")
def get_my_beneficiarios(
    q: Annotated[str | None, Query(description="Search beneficiary name or folio")] = None,
    status: Annotated[str | None, Query(description="Filter by status: borrador or completo")] = None,
    db: Annotated[_DBAdapter, Depends(get_db)] = None,
    user: Annotated[CurrentUser, Depends(require_roles("capturista", "organizacion", "admin"))] = None,
) -> list[dict]:
    """Return beneficiary list with edit links for the current user.

    Args:
        q: Optional search string to filter by beneficiary name or folio.
        status: Optional status filter ('borrador' or 'completo').
    """
    conditions = ["e.usuario_id = %s"]
    params: list = [user.usuario_id]

    if status is not None:
        conditions.append("e.status = %s")
        params.append(status)

    if q is not None:
        conditions.append("(b.nombre ILIKE %s OR b.folio ILIKE %s)")
        search_pattern = f"%{q}%"
        params.extend([search_pattern, search_pattern])

    where_clause = " AND ".join(conditions)

    rows = db.execute(
        f"""
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
        WHERE {where_clause}
        ORDER BY e.created_at DESC
        """,
        tuple(params),
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
    usuario_id: int | None = None,
) -> list[dict]:
    """List all organizations (admin only). Optionally filter by usuario_id."""
    if usuario_id is not None:
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
                o.activo,
                o.created_at
            FROM organizaciones o
            WHERE o.usuario_id = %s
            ORDER BY o.id
            """,
            (usuario_id,),
        ).fetchall()
    else:
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
                o.activo,
                o.created_at
            FROM organizaciones o
            ORDER BY o.id
            """,
        ).fetchall()

    result = []
    for r in rows:
        org = dict(r)

        # Get all leaders
        leaders = db.execute(
            """
            SELECT u.id, u.nombre, u.email, u.rol
            FROM usuarios u
            JOIN organizaciones_lideres ol ON ol.usuario_id = u.id
            WHERE ol.organizacion_id = %s AND u.activo = TRUE
            """,
            (org["id"],),
        ).fetchall()
        org["lideres"] = [dict(l) for l in leaders]

        # Get member count
        member_count = db.execute(
            "SELECT COUNT(*) AS count FROM organizaciones_miembros WHERE organizacion_id = %s",
            (org["id"],),
        ).fetchone()["count"]
        org["member_count"] = member_count

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
    """Create a new organization + optionally its user account (admin only).
    
    If usuario_id is provided, links to existing user instead of creating one.
    """
    nombre = body.nombre.strip()
    if len(nombre) < 2 or len(nombre) > 200:
        raise HTTPException(status_code=422, detail="nombre debe tener entre 2 y 200 caracteres")

    # Check uniqueness
    existing_org = db.execute(
        "SELECT id FROM organizaciones WHERE nombre = %s", (nombre,),
    ).fetchone()
    if existing_org is not None:
        raise HTTPException(status_code=409, detail="Ya existe una organización con ese nombre")

    if body.usuario_id is not None:
        # Link to existing user
        user_row = db.execute(
            "SELECT id, email, activo FROM usuarios WHERE id = %s",
            (body.usuario_id,),
        ).fetchone()
        if user_row is None or not user_row["activo"]:
            raise HTTPException(status_code=400, detail="Usuario no encontrado o inactivo")
        usuario_id = user_row["id"]
        email = user_row["email"]
    else:
        # Create new user account
        if not body.email or len(body.email.strip()) < 5:
            raise HTTPException(status_code=422, detail="email inválido")
        email = body.email.strip().lower()

        if not body.password or len(body.password.strip()) < 8:
            raise HTTPException(status_code=422, detail="contraseña debe tener al menos 8 caracteres")

        existing_user = db.execute(
            "SELECT id FROM usuarios WHERE email = %s", (email,),
        ).fetchone()
        if existing_user is not None:
            raise HTTPException(status_code=409, detail="Ya existe un usuario con ese email")

        password_hash = _hash_password(body.password.strip())
        user_row = db.execute(
            """
            INSERT INTO usuarios (nombre, email, password_hash, rol)
            VALUES (%s, %s, %s, 'organizacion')
            RETURNING id
            """,
            (nombre, email, password_hash),
        ).fetchone()
        usuario_id = user_row["id"]

    # Create the organization linked to the user
    org_row = db.execute(
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
            email,
            usuario_id,
        ),
    ).fetchone()

    return {
        "id": org_row["id"],
        "nombre": org_row["nombre"],
        "usuario_id": usuario_id,
        "email": email,
    }


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
            o.activo,
            o.created_at
        FROM organizaciones o
        WHERE o.id = %s
        """,
        (org_id,),
    ).fetchone()

    if org is None:
        raise HTTPException(status_code=404, detail="Organización no encontrada")

    result = dict(org)

    # Get all leaders
    leaders = db.execute(
        """
        SELECT u.id, u.nombre, u.email, u.rol
        FROM usuarios u
        JOIN organizaciones_lideres ol ON ol.usuario_id = u.id
        WHERE ol.organizacion_id = %s AND u.activo = TRUE
        """,
        (org_id,),
    ).fetchall()
    result["lideres"] = [dict(l) for l in leaders]

    # Get all members
    members = db.execute(
        """
        SELECT u.id, u.nombre, u.email, u.rol
        FROM usuarios u
        JOIN organizaciones_miembros om ON om.usuario_id = u.id
        WHERE om.organizacion_id = %s AND u.activo = TRUE
        """,
        (org_id,),
    ).fetchall()
    result["miembros"] = [dict(m) for m in members]

    # Get stats and heatmap for the org's usuario_id
    if org["usuario_id"]:
        result["stats"] = _get_user_stats(db, org["usuario_id"])
        result["heatmap_data"] = _get_heatmap_data(db, org["usuario_id"])
    else:
        result["stats"] = {"total_capturas": 0, "this_month": 0}
        result["heatmap_data"] = []

    return result


class OrganizacionUpdateRequest(BaseModel):
    descripcion: str | None = None
    direccion: str | None = None
    telefono: str | None = None


@router.patch("/organizaciones/{org_id}")
def update_organizacion(
    org_id: int,
    body: OrganizacionUpdateRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    _admin: Annotated[CurrentUser, Depends(require_admin)],
) -> dict:
    """Update organization details (admin only)."""
    org = db.execute(
        "SELECT id FROM organizaciones WHERE id = %s",
        (org_id,),
    ).fetchone()
    if org is None:
        raise HTTPException(status_code=404, detail="Organización no encontrada")

    updates = {}
    if body.descripcion is not None:
        updates["descripcion"] = body.descripcion.strip()
    if body.direccion is not None:
        updates["direccion"] = body.direccion.strip()
    if body.telefono is not None:
        updates["telefono"] = body.telefono.strip()

    if updates:
        set_clause = ", ".join(f"{k} = %s" for k in updates)
        values = list(updates.values())
        values.append(org_id)
        db.execute(
            f"UPDATE organizaciones SET {set_clause} WHERE id = %s",
            values,
        )

    return {"id": org_id, "message": "Organización actualizada"}


@router.post("/organizaciones/{org_id}/lider")
def add_org_lider(
    org_id: int,
    body: LiderAssignRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    _admin: Annotated[CurrentUser, Depends(require_admin)],
) -> dict:
    """Add a leader to an organization (admin only). Ignores duplicates."""
    org = db.execute(
        "SELECT id FROM organizaciones WHERE id = %s",
        (org_id,),
    ).fetchone()
    if org is None:
        raise HTTPException(status_code=404, detail="Organización no encontrada")

    if body.lider_usuario_id is None:
        raise HTTPException(status_code=400, detail="lider_usuario_id es requerido")

    # Verify user exists and is active
    user = db.execute(
        "SELECT id, activo FROM usuarios WHERE id = %s",
        (body.lider_usuario_id,),
    ).fetchone()
    if user is None or not user["activo"]:
        raise HTTPException(status_code=400, detail="Usuario no encontrado o inactivo")

    db.execute(
        """
        INSERT INTO organizaciones_lideres (organizacion_id, usuario_id)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
        """,
        (org_id, body.lider_usuario_id),
    )

    return {"message": "Líder agregado"}


@router.delete("/organizaciones/{org_id}/lider/{usuario_id}")
def remove_org_lider(
    org_id: int,
    usuario_id: int,
    db: Annotated[_DBAdapter, Depends(get_db)],
    _admin: Annotated[CurrentUser, Depends(require_admin)],
) -> dict:
    """Remove a leader from an organization (admin only)."""
    org = db.execute(
        "SELECT id FROM organizaciones WHERE id = %s",
        (org_id,),
    ).fetchone()
    if org is None:
        raise HTTPException(status_code=404, detail="Organización no encontrada")

    db.execute(
        "DELETE FROM organizaciones_lideres WHERE organizacion_id = %s AND usuario_id = %s",
        (org_id, usuario_id),
    )
    return {"message": "Líder eliminado"}


@router.post("/organizaciones/{org_id}/miembros")
def add_org_member(
    org_id: int,
    body: LiderAssignRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    _admin: Annotated[CurrentUser, Depends(require_admin)],
) -> dict:
    """Add a member to an organization (admin only). Ignores duplicates."""
    org = db.execute(
        "SELECT id FROM organizaciones WHERE id = %s",
        (org_id,),
    ).fetchone()
    if org is None:
        raise HTTPException(status_code=404, detail="Organización no encontrada")

    if body.lider_usuario_id is None:
        raise HTTPException(status_code=400, detail="usuario_id es requerido")

    user = db.execute(
        "SELECT id, activo FROM usuarios WHERE id = %s",
        (body.lider_usuario_id,),
    ).fetchone()
    if user is None or not user["activo"]:
        raise HTTPException(status_code=400, detail="Usuario no encontrado o inactivo")

    db.execute(
        """
        INSERT INTO organizaciones_miembros (organizacion_id, usuario_id)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
        """,
        (org_id, body.lider_usuario_id),
    )
    return {"message": "Miembro agregado"}


@router.delete("/organizaciones/{org_id}/miembros/{usuario_id}")
def remove_org_member(
    org_id: int,
    usuario_id: int,
    db: Annotated[_DBAdapter, Depends(get_db)],
    _admin: Annotated[CurrentUser, Depends(require_admin)],
) -> dict:
    """Remove a member from an organization (admin only)."""
    org = db.execute(
        "SELECT id FROM organizaciones WHERE id = %s",
        (org_id,),
    ).fetchone()
    if org is None:
        raise HTTPException(status_code=404, detail="Organización no encontrada")

    db.execute(
        "DELETE FROM organizaciones_miembros WHERE organizacion_id = %s AND usuario_id = %s",
        (org_id, usuario_id),
    )
    return {"message": "Miembro eliminado"}


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
        "SELECT id FROM organizaciones WHERE id = %s AND activo = TRUE",
        (org_id,),
    ).fetchone()
    if org is None:
        raise HTTPException(status_code=404, detail="Organización no encontrada")

    rows = db.execute(
        """
        SELECT nombre, contacto, capturas_count, ultima_captura, created_at
        FROM organizaciones_voluntarios
        WHERE organizacion_id = %s
        ORDER BY capturas_count DESC, ultima_captura DESC
        """,
        (org_id,),
    ).fetchall()

    return [
        {
            "nombre": r["nombre"],
            "contacto": r["contacto"],
            "capturas": r["capturas_count"],
            "ultima_captura": r["ultima_captura"].isoformat() if r["ultima_captura"] else None,
            "registrado": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]
