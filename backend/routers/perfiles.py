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

def _get_user_stats(db: _DBAdapter, usuario_id: int) -> tuple[dict, str | None]:
    """Return ({total_capturas, this_month, pendientes}, last_activity_iso) for a user.

    Stats and last-activity are computed in a single scan of
    estudios_socioeconomicos — /me/perfil is the most-visited capturista page,
    so collapsing what were two sequential round-trips into one matters.

    last_activity uses MAX(GREATEST(created_at, COALESCE(updated_at, created_at))):
    COALESCE guards against GREATEST returning NULL (and MAX skipping the row)
    when updated_at was never backfilled.
    """
    now = datetime.now(timezone.utc)
    row = db.execute(
        "SELECT COUNT(*) AS total, "
        "COUNT(*) FILTER (WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', %s::timestamptz)) AS this_month, "
        "COUNT(*) FILTER (WHERE status = 'borrador') AS pendientes, "
        "MAX(GREATEST(created_at, COALESCE(updated_at, created_at))) AS last_activity_date "
        "FROM estudios_socioeconomicos WHERE usuario_id = %s",
        (now, usuario_id),
    ).fetchone()

    last_activity_date = row["last_activity_date"]
    if last_activity_date is not None:
        last_activity_date = last_activity_date.isoformat()

    stats = {
        "total_capturas": row["total"],
        "this_month": row["this_month"],
        "pendientes": row["pendientes"],
    }
    return stats, last_activity_date


def _get_org_user_ids(db: _DBAdapter, org_id: int) -> list[int]:
    """Return every usuario_id whose captures count for an organization:
    the org's own account (volunteer/guest captures run through it),
    its leaders, and its members."""
    rows = db.execute(
        """
        SELECT usuario_id FROM organizaciones WHERE id = %s AND usuario_id IS NOT NULL
        UNION
        SELECT ol.usuario_id FROM organizaciones_lideres ol WHERE ol.organizacion_id = %s
        UNION
        SELECT om.usuario_id FROM organizaciones_miembros om WHERE om.organizacion_id = %s
        """,
        (org_id, org_id, org_id),
    ).fetchall()
    return [r["usuario_id"] for r in rows]


def _assert_org_access(db: _DBAdapter, org_id: int, user: CurrentUser) -> None:
    """Capture-level data (beneficiarios, voluntarios) is visible only to
    admins and the organization's own account. Visitors — including leaders
    and members browsing the org page — see identity and stats only."""
    if user.rol == "admin":
        return
    org = db.execute(
        "SELECT usuario_id FROM organizaciones WHERE id = %s",
        (org_id,),
    ).fetchone()
    if org is not None and org["usuario_id"] == user.usuario_id:
        return
    raise HTTPException(
        status_code=403,
        detail="Solo la organización puede ver el detalle de sus capturas",
    )


def _get_org_stats(db: _DBAdapter, user_ids: list[int]) -> dict:
    """Aggregate capture stats across all of an organization's users."""
    if not user_ids:
        return {"total_capturas": 0, "this_month": 0, "completados": 0, "pendientes": 0}
    now = datetime.now(timezone.utc)
    row = db.execute(
        "SELECT COUNT(*) AS total, "
        "COUNT(*) FILTER (WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', %s::timestamptz)) AS this_month, "
        "COUNT(*) FILTER (WHERE status = 'completo') AS completados, "
        "COUNT(*) FILTER (WHERE status = 'borrador') AS pendientes "
        "FROM estudios_socioeconomicos WHERE usuario_id = ANY(%s)",
        (now, user_ids),
    ).fetchone()
    return {
        "total_capturas": row["total"],
        "this_month": row["this_month"],
        "completados": row["completados"],
        "pendientes": row["pendientes"],
    }


def _get_org_heatmap_data(db: _DBAdapter, user_ids: list[int]) -> list[dict]:
    """Aggregate last-365-days heatmap across all of an organization's users."""
    if not user_ids:
        return []
    rows = db.execute(
        "SELECT DATE(created_at AT TIME ZONE 'UTC') AS date, COUNT(*) AS count "
        "FROM estudios_socioeconomicos "
        "WHERE usuario_id = ANY(%s) AND created_at >= NOW() - INTERVAL '1 year' "
        "GROUP BY DATE(created_at AT TIME ZONE 'UTC') "
        "ORDER BY date",
        (user_ids,),
    ).fetchall()
    return [{"date": str(r["date"]), "count": r["count"]} for r in rows]


def _get_heatmap_data(db: _DBAdapter, usuario_id: int, year: int | None = None) -> list[dict]:
    """Return [{date: str, count: int}] for a user's activity.

    Args:
        year: Optional calendar year to filter by. Defaults to last 365 days
              if not provided (backward-compatible).
    """
    # DATE() on a TIMESTAMPTZ truncates using the session TimeZone; force UTC so
    # buckets always match the UTC range filter and the frontend's UTC day keys.
    if year is not None:
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        next_start = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        rows = db.execute(
            "SELECT DATE(created_at AT TIME ZONE 'UTC') AS date, COUNT(*) AS count "
            "FROM estudios_socioeconomicos "
            "WHERE usuario_id = %s AND created_at >= %s AND created_at < %s "
            "GROUP BY DATE(created_at AT TIME ZONE 'UTC') "
            "ORDER BY date",
            (usuario_id, start, next_start),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT DATE(created_at AT TIME ZONE 'UTC') AS date, COUNT(*) AS count "
            "FROM estudios_socioeconomicos "
            "WHERE usuario_id = %s AND created_at >= NOW() - INTERVAL '1 year' "
            "GROUP BY DATE(created_at AT TIME ZONE 'UTC') "
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

    # Stats and last-activity come from a single scan (see _get_user_stats).
    stats, last_activity_date = _get_user_stats(db, user.usuario_id)

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
            e.id                      AS estudio_id,
            e.beneficiario_id,
            e.usuario_id,
            e.otras_fuentes_ingreso,
            e.monto_otras_fuentes,
            e.tuvo_silla_previa,
            e.como_obtuvo_silla,
            e.elaboro_estudio,
            e.fecha_estudio,
            e.sede,
            e.ciudad_registro,
            e.credencial_path,
            e.credencial_url,
            e.comprobante_domicilio_path,
            e.comprobante_domicilio_url,
            e.status,
            e.finalizado_at,
            e.created_at,
            e.updated_at,
            b.id                      AS beneficiario_id,
            b.nombre                  AS beneficiario_nombre,
            b.nombres,
            b.apellido_paterno,
            b.apellido_materno,
            b.fecha_nacimiento,
            b.diagnostico,
            b.calle,
            b.num_ext,
            b.num_int,
            b.colonia,
            b.ciudad,
            b.estado_codigo,
            b.estado_nombre,
            b.sexo,
            b.telefonos,
            b.email,
            b.folio,
            b.region_id,
            b.created_at              AS beneficiario_created_at
        FROM estudios_socioeconomicos e
        JOIN beneficiarios b ON b.id = e.beneficiario_id
        WHERE {where_clause}
        ORDER BY e.created_at DESC
        """,
        tuple(params),
    ).fetchall()

    # Get all tutors for these beneficiaries in one query
    beneficiario_ids = list({r["beneficiario_id"] for r in rows})
    tutors_by_beneficiario: dict[int, list[dict]] = {}
    if beneficiario_ids:
        placeholders = ",".join(["%s"] * len(beneficiario_ids))
        tutor_rows = db.execute(
            f"""
            SELECT * FROM tutores
            WHERE beneficiario_id IN ({placeholders})
            ORDER BY numero_tutor
            """,
            tuple(beneficiario_ids),
        ).fetchall()
        for t in tutor_rows:
            bid = t["beneficiario_id"]
            tutors_by_beneficiario.setdefault(bid, []).append(dict(t))

    result = []
    for r in rows:
        estudio = dict(r)
        # Remove duplicated columns
        estudio.pop("beneficiario_id", None)
        estudio["beneficiario"] = {
            "id": r["beneficiario_id"],
            "nombre": r["beneficiario_nombre"],
            "nombres": r["nombres"],
            "apellido_paterno": r["apellido_paterno"],
            "apellido_materno": r["apellido_materno"],
            "fecha_nacimiento": str(r["fecha_nacimiento"]) if r["fecha_nacimiento"] else None,
            "diagnostico": r["diagnostico"],
            "calle": r["calle"],
            "num_ext": r["num_ext"],
            "num_int": r["num_int"],
            "colonia": r["colonia"],
            "ciudad": r["ciudad"],
            "estado_codigo": r["estado_codigo"],
            "estado_nombre": r["estado_nombre"],
            "telefonos": r["telefonos"],
            "email": r["email"],
            "sexo": r["sexo"],
            "folio": r["folio"],
            "region_id": r["region_id"],
        }
        estudio["tutores"] = tutors_by_beneficiario.get(r["beneficiario_id"], [])
        estudio["edit_url"] = f"socioeconomico.html?estudio_id={r['estudio_id']}"
        # Clean up FastAPI serialization issues
        for key in list(estudio.keys()):
            if estudio[key] is None:
                continue
            if hasattr(estudio[key], "isoformat"):
                estudio[key] = estudio[key].isoformat()
        result.append(estudio)

    return result


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

        # Total capturas = org account (volunteers) + leaders + members
        org_user_ids = _get_org_user_ids(db, org["id"])
        org["total_capturas"] = _get_org_stats(db, org_user_ids)["total_capturas"]
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

    # Aggregate stats across the org account (volunteer captures),
    # leaders, and members
    org_user_ids = _get_org_user_ids(db, org_id)
    result["stats"] = _get_org_stats(db, org_user_ids)
    result["heatmap_data"] = _get_org_heatmap_data(db, org_user_ids)

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
    """Return aggregate heatmap data for an organization (org account +
    leaders + members)."""
    org = db.execute(
        "SELECT id FROM organizaciones WHERE id = %s",
        (org_id,),
    ).fetchone()
    if org is None:
        raise HTTPException(status_code=404, detail="Organización no encontrada")
    return _get_org_heatmap_data(db, _get_org_user_ids(db, org_id))


@router.get("/organizaciones/{org_id}/beneficiarios")
def get_org_beneficiarios(
    org_id: int,
    db: Annotated[_DBAdapter, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(require_auth)],
) -> list[dict]:
    """Beneficiaries captured by the organization: every estudio made by
    the org account (volunteers), its leaders, or its members."""
    org = db.execute(
        "SELECT id FROM organizaciones WHERE id = %s",
        (org_id,),
    ).fetchone()
    if org is None:
        raise HTTPException(status_code=404, detail="Organización no encontrada")

    _assert_org_access(db, org_id, user)

    user_ids = _get_org_user_ids(db, org_id)
    if not user_ids:
        return []

    rows = db.execute(
        """
        SELECT
            e.id AS estudio_id,
            e.status,
            e.created_at,
            COALESCE(e.elaboro_estudio, u.nombre) AS elaboro_estudio,
            b.nombre AS beneficiario_nombre,
            b.folio
        FROM estudios_socioeconomicos e
        JOIN beneficiarios b ON b.id = e.beneficiario_id
        LEFT JOIN usuarios u ON u.id = e.usuario_id
        WHERE e.usuario_id = ANY(%s)
        ORDER BY e.created_at DESC
        """,
        (user_ids,),
    ).fetchall()

    return [
        {
            "estudio_id": r["estudio_id"],
            "beneficiario_nombre": r["beneficiario_nombre"],
            "folio": r["folio"],
            "status": r["status"],
            "elaboro_estudio": r["elaboro_estudio"],
            "fecha": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


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

    _assert_org_access(db, org_id, user)

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
