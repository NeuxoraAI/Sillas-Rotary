"""
Admin router — endpoints for beneficiario management by admin role.
"""

import io
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator, model_validator, ValidationInfo
from decimal import Decimal

from database import get_db, _DBAdapter
from routers.auth import CurrentUser, require_roles
from routers.tecnica import (
    _build_list_where_clause,
    _build_snapshot,
    _calcular_edad,
)
from routers.socioeconomico import _resolve_como_obtuvo_silla
from validators import (
    validate_nombre,
    validate_apellido,
    validate_email_format,
    validate_diagnostico,
    validate_calle,
    validate_colonia,
    validate_ciudad,
    validate_numero_domicilio,
    validate_telefono,
    validate_estado_codigo,
    validate_estado_nombre,
    validate_sexo,
    validate_fecha_nacimiento,
    validate_entidad_solicitante,
    validate_justificacion,
    validate_prioridad,
    validate_padecimiento,
    validate_medida_tecnica,
    validate_entorno,
    validate_control_tronco,
    validate_control_cabeza,
    validate_control_de_piernas,
    validate_unidad_medida,
    validate_unidad_peso,
    validate_status,
)

from utils.text import normalize_text

router = APIRouter()


def _row_to_dict(row) -> Optional[dict]:
    if row is None:
        return None
    return dict(row)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class AdminBeneficiarioUpdateRequest(BaseModel):
    """Editable beneficiario fields by admin. Folio and region_id are readonly."""
    nombres: Optional[str] = None
    apellido_paterno: Optional[str] = None
    apellido_materno: Optional[str] = None
    fecha_nacimiento: Optional[str] = None
    diagnostico: Optional[str] = None
    calle: Optional[str] = None
    num_ext: Optional[str] = None
    num_int: Optional[str] = None
    colonia: Optional[str] = None
    ciudad: Optional[str] = None
    estado_codigo: Optional[str] = None
    estado_nombre: Optional[str] = None
    sexo: Optional[str] = None
    telefonos: Optional[str] = None
    email: Optional[str] = None

    @field_validator("nombres", "apellido_paterno", "apellido_materno",
                      "diagnostico", "calle", "colonia", "ciudad", mode="before")
    @classmethod
    def _normalizar_textos(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return normalize_text(v)

    @field_validator("num_ext", "num_int", mode="before")
    @classmethod
    def _validar_numero_domicilio(cls, v: Optional[str]) -> Optional[str]:
        if v == "":
            return v
        return validate_numero_domicilio(v)

    @field_validator("nombres")
    @classmethod
    def _validar_nombres(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_nombre(v)

    @field_validator("apellido_paterno")
    @classmethod
    def _validar_apellido_paterno(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_apellido(v, "apellido_paterno")

    @field_validator("apellido_materno")
    @classmethod
    def _validar_apellido_materno(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_apellido(v, "apellido_materno")

    @field_validator("fecha_nacimiento")
    @classmethod
    def _fecha_nacimiento_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_fecha_nacimiento(v)

    @field_validator("sexo")
    @classmethod
    def _sexo_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_sexo(v)

    @field_validator("diagnostico")
    @classmethod
    def _diagnostico_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_diagnostico(v)

    @field_validator("calle")
    @classmethod
    def _calle_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_calle(v)

    @field_validator("colonia")
    @classmethod
    def _colonia_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_colonia(v)

    @field_validator("ciudad")
    @classmethod
    def _ciudad_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_ciudad(v)

    @field_validator("estado_codigo")
    @classmethod
    def _estado_codigo_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_estado_codigo(v)

    @field_validator("estado_nombre")
    @classmethod
    def _estado_nombre_consistente(cls, v: Optional[str], info) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_estado_nombre(v, info.data.get("estado_codigo"))

    @field_validator("telefonos")
    @classmethod
    def _telefonos_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_telefono(v)

    @field_validator("email")
    @classmethod
    def _email_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_email_format(v)


class AdminEstudioUpdateRequest(BaseModel):
    """Admin edit of estudio fields (no owner check)."""
    tuvo_silla_previa: Optional[bool] = None
    como_obtuvo_silla: Optional[str] = None
    fecha_estudio: Optional[str] = None
    sede: Optional[str] = None
    ciudad_registro: Optional[str] = None
    status: Optional[str] = None
    elaboro_estudio: Optional[str] = None

    @field_validator("status")
    @classmethod
    def _status_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_status(v)

    @field_validator("como_obtuvo_silla", "ciudad_registro", mode="before")
    @classmethod
    def _normalizar(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return normalize_text(v)

    @model_validator(mode="after")
    def _validar_fecha_estudio_completo(self):
        if self.status == "completo":
            if not self.fecha_estudio:
                raise ValueError("fecha_estudio es obligatorio cuando status es completo")
            if self.tuvo_silla_previa is None:
                raise ValueError("tuvo_silla_previa es obligatorio cuando status es completo")
            if self.tuvo_silla_previa is True and (self.como_obtuvo_silla is None or self.como_obtuvo_silla == ""):
                raise ValueError("como_obtuvo_silla es obligatorio cuando tuvo_silla_previa es verdadero")
        return self


class AdminSolicitudUpdateRequest(BaseModel):
    """Admin edit of solicitud fields (no owner check)."""
    entorno: Optional[str] = None
    control_tronco: Optional[str] = None
    control_cabeza: Optional[str] = None
    control_de_piernas: Optional[str] = None
    padecimiento: Optional[str] = None
    unidad_medida: Optional[str] = None
    altura_total_in: Optional[Decimal] = None
    peso_kg: Optional[Decimal] = None
    unidad_peso_captura: Optional[str] = None
    medida_cabeza_asiento: Optional[Decimal] = None
    medida_hombro_asiento: Optional[Decimal] = None
    medida_prof_asiento: Optional[Decimal] = None
    medida_rodilla_talon: Optional[Decimal] = None
    medida_ancho_cadera: Optional[Decimal] = None
    entidad_solicitante: Optional[str] = None
    prioridad: Optional[str] = None
    justificacion: Optional[str] = None
    status: Optional[str] = None

    @field_validator("entorno")
    @classmethod
    def _entorno_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_entorno(v)

    @field_validator("control_tronco")
    @classmethod
    def _control_tronco_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_control_tronco(v)

    @field_validator("control_cabeza")
    @classmethod
    def _control_cabeza_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_control_cabeza(v)

    @field_validator("control_de_piernas")
    @classmethod
    def _control_de_piernas_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_control_de_piernas(v)

    @field_validator("padecimiento", mode="before")
    @classmethod
    def validate_obs_field(cls, v) -> Optional[str]:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return validate_padecimiento(str(v))

    @field_validator("unidad_medida")
    @classmethod
    def _unidad_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_unidad_medida(v)

    @field_validator("unidad_peso_captura")
    @classmethod
    def _unidad_peso_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_unidad_peso(v)

    @field_validator("altura_total_in", "peso_kg", "medida_cabeza_asiento",
                     "medida_hombro_asiento", "medida_prof_asiento",
                     "medida_rodilla_talon", "medida_ancho_cadera", mode="before")
    @classmethod
    def validate_medida_field(cls, v, info: ValidationInfo) -> Optional[Decimal]:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return validate_medida_tecnica(str(v), info.field_name)

    @field_validator("entidad_solicitante", mode="before")
    @classmethod
    def validate_entidad_solicitante_field(cls, v) -> Optional[str]:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return validate_entidad_solicitante(str(v))

    @field_validator("prioridad")
    @classmethod
    def _prioridad_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_prioridad(v)

    @field_validator("justificacion", mode="before")
    @classmethod
    def validate_justificacion_field(cls, v) -> Optional[str]:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return validate_justificacion(str(v))

    @field_validator("status")
    @classmethod
    def _status_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_status(v)


class AdminGestionUpdateRequest(BaseModel):
    """Atomic update of estudio + solicitud in one transaction."""
    # Estudio fields
    tuvo_silla_previa: Optional[bool] = None
    como_obtuvo_silla: Optional[str] = None
    fecha_estudio: Optional[str] = None
    sede: Optional[str] = None
    ciudad_registro: Optional[str] = None
    elaboro_estudio: Optional[str] = None
    status_estudio: Optional[str] = None
    # Solicitud fields
    entidad_solicitante: Optional[str] = None
    prioridad: Optional[str] = None
    justificacion: Optional[str] = None

    @field_validator("como_obtuvo_silla", "ciudad_registro", mode="before")
    @classmethod
    def _normalizar(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return normalize_text(v)

    @field_validator("status_estudio")
    @classmethod
    def _status_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_status(v)

    @field_validator("entidad_solicitante", mode="before")
    @classmethod
    def _entidad_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return validate_entidad_solicitante(str(v))

    @field_validator("prioridad")
    @classmethod
    def _prioridad_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return validate_prioridad(v)

    @field_validator("justificacion", mode="before")
    @classmethod
    def _justificacion_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return validate_justificacion(str(v))

    @model_validator(mode="after")
    def _validar_estudio_completo(self):
        if self.status_estudio == "completo":
            if not self.fecha_estudio:
                raise ValueError("fecha_estudio es obligatorio cuando status es completo")
            if self.tuvo_silla_previa is None:
                raise ValueError("tuvo_silla_previa es obligatorio cuando status es completo")
            if self.tuvo_silla_previa is True and (self.como_obtuvo_silla is None or self.como_obtuvo_silla == ""):
                raise ValueError("como_obtuvo_silla es obligatorio cuando tuvo_silla_previa es verdadero")
        return self


# ---------------------------------------------------------------------------
# Helper: ensure beneficiario exists
# ---------------------------------------------------------------------------

def _ensure_beneficiario(db: _DBAdapter, beneficiario_id: int) -> dict:
    row = _row_to_dict(
        db.execute("SELECT * FROM beneficiarios WHERE id = %s", (beneficiario_id,)).fetchone()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Beneficiario no encontrado")
    return row


def _ensure_estudio(db: _DBAdapter, beneficiario_id: int) -> dict:
    row = _row_to_dict(
        db.execute(
            "SELECT * FROM estudios_socioeconomicos WHERE beneficiario_id = %s ORDER BY id DESC LIMIT 1",
            (beneficiario_id,),
        ).fetchone()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Estudio no encontrado para este beneficiario")
    return row


def _ensure_solicitud(db: _DBAdapter, beneficiario_id: int) -> dict:
    row = _row_to_dict(
        db.execute(
            "SELECT * FROM solicitudes_tecnicas WHERE beneficiario_id = %s ORDER BY id DESC LIMIT 1",
            (beneficiario_id,),
        ).fetchone()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada para este beneficiario")
    return row


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/admin/beneficiarios")
def listar_beneficiarios_admin(
    db: Annotated[_DBAdapter, Depends(get_db)],
    _usuario: Annotated[CurrentUser, Depends(require_roles("admin"))],
    q: Optional[str] = None,
    sede: Optional[str] = None,
    estado: Optional[str] = None,
    revision_pendiente: Optional[bool] = None,
    pais_id: Optional[int] = None,
    region_id: Optional[int] = None,
    ciudad: Optional[str] = None,
    peso_kg_min: Optional[float] = None,
    peso_kg_max: Optional[float] = None,
    altura_in_min: Optional[float] = None,
    altura_in_max: Optional[float] = None,
    tiene_foto: Optional[bool] = None,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    """List beneficiarios with filters and pagination. Admin only."""
    if page < 1:
        raise HTTPException(status_code=422, detail={"type": "invalid_filter", "message": "page debe ser >= 1"})
    if per_page < 1:
        raise HTTPException(status_code=422, detail={"type": "invalid_filter", "message": "per_page debe ser >= 1"})

    where_clause, params = _build_list_where_clause(
        q=q, sede=sede, estado=estado, revision_pendiente=revision_pendiente,
        pais_id=pais_id, region_id=region_id, ciudad=ciudad,
        peso_kg_min=peso_kg_min, peso_kg_max=peso_kg_max,
        altura_in_min=altura_in_min, altura_in_max=altura_in_max,
        tiene_foto=tiene_foto,
    )

    offset = (page - 1) * per_page

    rows = db.execute(
        f"""
        SELECT
            b.id AS beneficiario_id,
            b.nombre,
            b.folio,
            b.telefonos,
            b.ciudad,
            COALESCE(p.nombre, '') AS pais_nombre,
            COALESCE(r.nombre, '') AS region_nombre,
            COALESCE(e.sede, '') AS sede,
            COALESCE(pt.estado, 'sin_iniciar') AS estado,
            COALESCE(pt.revision_pendiente, FALSE) AS revision_pendiente,
            pt.id AS proceso_id,
            st.peso_kg,
            st.altura_total_in,
            st.unidad_captura,
            st.foto_url,
            COUNT(*) OVER() AS total_count
        FROM beneficiarios b
        LEFT JOIN estudios_socioeconomicos e ON e.beneficiario_id = b.id
        LEFT JOIN procesos_tecnicos pt ON pt.beneficiario_id = b.id
        LEFT JOIN solicitudes_tecnicas st ON st.beneficiario_id = b.id
        LEFT JOIN regiones r ON r.id = b.region_id
        LEFT JOIN paises p ON p.id = r.pais_id
        WHERE {where_clause}
        ORDER BY b.nombre ASC
        LIMIT %s OFFSET %s
        """,
        tuple(params) + (per_page, offset),
    ).fetchall()

    total = rows[0]["total_count"] if rows else 0

    return {"items": rows, "total": total, "page": page, "per_page": per_page}


@router.get("/admin/beneficiarios/export")
def exportar_beneficiarios_admin(
    db: Annotated[_DBAdapter, Depends(get_db)],
    _usuario: Annotated[CurrentUser, Depends(require_roles("admin"))],
    q: Optional[str] = None,
    sede: Optional[str] = None,
    estado: Optional[str] = None,
    revision_pendiente: Optional[bool] = None,
    pais_id: Optional[int] = None,
    region_id: Optional[int] = None,
    ciudad: Optional[str] = None,
    peso_kg_min: Optional[float] = None,
    peso_kg_max: Optional[float] = None,
    altura_in_min: Optional[float] = None,
    altura_in_max: Optional[float] = None,
    tiene_foto: Optional[bool] = None,
    ids: Optional[str] = None,
) -> StreamingResponse:
    """Export beneficiarios to Excel. Admin only."""
    where_clause, params = _build_list_where_clause(
        q=q, sede=sede, estado=estado, revision_pendiente=revision_pendiente,
        pais_id=pais_id, region_id=region_id, ciudad=ciudad,
        peso_kg_min=peso_kg_min, peso_kg_max=peso_kg_max,
        altura_in_min=altura_in_min, altura_in_max=altura_in_max,
        tiene_foto=tiene_foto,
    )

    ids_list: list[int] = []
    if ids:
        try:
            ids_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(status_code=422, detail={"type": "invalid_filter", "message": "ids debe ser una lista de enteros separados por coma"})
    if ids_list:
        placeholders = ",".join(["%s"] * len(ids_list))
        where_clause += f" AND b.id IN ({placeholders})"
        params.extend(ids_list)

    rows = db.execute(
        f"""
        SELECT
            b.id AS beneficiario_id,
            b.folio,
            b.nombre,
            b.email,
            b.calle,
            b.num_ext,
            b.colonia,
            b.ciudad,
            b.estado_nombre,
            b.telefonos,
            b.diagnostico,
            b.fecha_nacimiento,
            st.peso_kg,
            st.altura_total_in,
            st.unidad_captura,
            st.padecimiento,
            st.justificacion,
            st.entidad_solicitante,
            t.nombre AS tutor_nombre
        FROM beneficiarios b
        LEFT JOIN estudios_socioeconomicos e ON e.beneficiario_id = b.id
        LEFT JOIN procesos_tecnicos pt ON pt.beneficiario_id = b.id
        LEFT JOIN solicitudes_tecnicas st ON st.beneficiario_id = b.id
        LEFT JOIN regiones r ON r.id = b.region_id
        LEFT JOIN paises p ON p.id = r.pais_id
        LEFT JOIN LATERAL (
            SELECT nombre FROM tutores WHERE beneficiario_id = b.id ORDER BY numero_tutor LIMIT 1
        ) t ON true
        WHERE {where_clause}
        ORDER BY b.nombre ASC
        """,
        tuple(params),
    ).fetchall()

    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.table import Table, TableStyleInfo

    wb = Workbook()
    ws = wb.active
    ws.title = "MASTER"

    headers = [
        "# EXPEDIENTE",
        "Nombre de Niño(a) Adolescente",
        "Correo electrónico ",
        "Dirección (calle, numero)",
        "Colonia o comunidad",
        "Municipio (ciudad) y Estado",
        "Número de teléfono Fijo",
        "No. de teléfono adicional",
        "Padecimiento",
        "Fecha de nacimiento",
        "EDAD",
        "PESO (lb)",
        "ESTATURA (in)",
        "Nombre de Padre o tutor",
        "Club o A sociación",
        "QUIEN CANALIZA",
        "OBSERVACIONES ",
    ]

    ws.append([])
    ws.append(headers)

    header_fill = PatternFill(fill_type="solid", fgColor="1F4E78")
    header_font = Font(color="FFFFFF", bold=True)
    for cell in ws[2]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for row in rows:
        direccion = (row["calle"] or "") + (f' {row["num_ext"]}' if row.get("num_ext") else "")
        municipio_estado = (row["ciudad"] or "") + (f', {row["estado_nombre"]}' if row.get("estado_nombre") else "")
        altura_in = row.get("altura_total_in")
        edad = _calcular_edad(row.get("fecha_nacimiento"))

        ws.append([
            row.get("folio") or row.get("beneficiario_id"),
            row.get("nombre") or "",
            row.get("email") or "Sin correo",
            direccion,
            row.get("colonia") or "",
            municipio_estado,
            row.get("telefonos") or "",
            "",
            row.get("diagnostico") or "",
            row.get("fecha_nacimiento") or "",
            edad,
            row.get("peso_kg"),
            altura_in,
            row.get("tutor_nombre") or "",
            row.get("entidad_solicitante") or "",
            "",
            row.get("padecimiento") or "",
        ])

    ws.freeze_panes = "A3"

    column_widths = {"A": 18, "B": 34, "C": 24, "D": 28, "E": 24, "F": 28, "G": 20,
                     "H": 20, "I": 24, "J": 18, "K": 10, "L": 12, "M": 14, "N": 28,
                     "O": 24, "P": 22, "Q": 34}
    for col, width in column_widths.items():
        ws.column_dimensions[col].width = width

    if ws.max_row >= 2:
        table = Table(displayName="BeneficiariosAdmin", ref=f"A2:Q{ws.max_row}")
        style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False, showLastColumn=False,
                               showRowStripes=True, showColumnStripes=False)
        table.tableStyleInfo = style
        ws.add_table(table)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"BASE_DE_DATOS_EXPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/admin/beneficiarios/{beneficiario_id}")
def obtener_detalle_admin(
    beneficiario_id: int,
    db: Annotated[_DBAdapter, Depends(get_db)],
    _usuario: Annotated[CurrentUser, Depends(require_roles("admin"))],
) -> dict:
    """Get full detail of a beneficiario. Admin only."""
    snapshot = _build_snapshot(db, beneficiario_id)
    snapshot["permisos"] = {
        "can_edit": True,
        "can_delete": True,
    }
    return snapshot


def _nullify_empty_strings(fields: dict) -> dict:
    """Convert empty strings to None so psycopg2 writes NULL in the DB."""
    return {k: (None if v == "" else v) for k, v in fields.items()}


@router.patch("/admin/beneficiarios/{beneficiario_id}")
def actualizar_beneficiario_admin(
    beneficiario_id: int,
    body: AdminBeneficiarioUpdateRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    _usuario: Annotated[CurrentUser, Depends(require_roles("admin"))],
) -> dict:
    """Update beneficiario fields. Admin only — no owner check."""
    _ensure_beneficiario(db, beneficiario_id)

    fields = body.model_dump(exclude_none=True)
    if not fields:
        return {"beneficiario_id": beneficiario_id, "updated": False}

    fields = _nullify_empty_strings(fields)

    # Rebuild nombre from structured fields if all three are provided
    if "nombres" in fields or "apellido_paterno" in fields or "apellido_materno" in fields:
        current = _ensure_beneficiario(db, beneficiario_id)
        nombres = fields.get("nombres", current.get("nombres", ""))
        ap = fields.get("apellido_paterno", current.get("apellido_paterno", ""))
        am = fields.get("apellido_materno", current.get("apellido_materno", ""))
        fields["nombre"] = f"{nombres} {ap} {am}"

    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values())
    values.append(beneficiario_id)

    import logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    logger.debug(f"[ADMIN PATCH] SQL: UPDATE beneficiarios SET {set_clause} WHERE id = %s")
    logger.debug(f"[ADMIN PATCH] Values: {values}")

    db.execute(
        f"UPDATE beneficiarios SET {set_clause} WHERE id = %s",
        values,
    )

    return {"beneficiario_id": beneficiario_id, "updated": True}


@router.patch("/admin/beneficiarios/{beneficiario_id}/estudio")
def actualizar_estudio_admin(
    beneficiario_id: int,
    body: AdminEstudioUpdateRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    usuario: Annotated[CurrentUser, Depends(require_roles("admin"))],
) -> dict:
    """Update estudio. Admin only — no owner check."""
    estudio = _ensure_estudio(db, beneficiario_id)

    fields = body.model_dump(exclude_none=True)
    if not fields:
        return {"estudio_id": estudio["id"], "updated": False}

    fields = _nullify_empty_strings(fields)

    if "tuvo_silla_previa" in fields:
        fields["tuvo_silla_previa"] = int(fields["tuvo_silla_previa"])
        fields["como_obtuvo_silla"] = _resolve_como_obtuvo_silla(
            fields["tuvo_silla_previa"], fields.get("como_obtuvo_silla")
        )

    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values())
    values.append(estudio["id"])

    db.execute(
        f"UPDATE estudios_socioeconomicos SET {set_clause}, updated_at = NOW() WHERE id = %s",
        values,
    )

    return {"estudio_id": estudio["id"], "updated": True}


@router.patch("/admin/beneficiarios/{beneficiario_id}/solicitud")
def actualizar_solicitud_admin(
    beneficiario_id: int,
    body: AdminSolicitudUpdateRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    _usuario: Annotated[CurrentUser, Depends(require_roles("admin"))],
) -> dict:
    """Update solicitud. Admin only — no owner check."""
    solicitud = _ensure_solicitud(db, beneficiario_id)

    fields = body.model_dump(exclude_none=True)
    if not fields:
        return {"solicitud_id": solicitud["id"], "updated": False}

    fields = _nullify_empty_strings(fields)

    # Rename unidad_medida to unidad_captura for DB
    if "unidad_medida" in fields:
        fields["unidad_captura"] = fields.pop("unidad_medida")

    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values())
    values.append(solicitud["id"])

    db.execute(
        f"UPDATE solicitudes_tecnicas SET {set_clause}, updated_at = NOW() WHERE id = %s",
        values,
    )

    return {"solicitud_id": solicitud["id"], "updated": True}


@router.patch("/admin/beneficiarios/{beneficiario_id}/gestion")
def actualizar_gestion_admin(
    beneficiario_id: int,
    body: AdminGestionUpdateRequest,
    db: Annotated[_DBAdapter, Depends(get_db)],
    _usuario: Annotated[CurrentUser, Depends(require_roles("admin"))],
) -> dict:
    """Atomic update of estudio + solicitud in one transaction. Admin only."""
    estudio = _ensure_estudio(db, beneficiario_id)
    solicitud = _ensure_solicitud(db, beneficiario_id)

    updated_estudio = False
    updated_solicitud = False

    # Build estudio fields
    estudio_fields = {}
    estudio_field_keys = [
        "tuvo_silla_previa", "como_obtuvo_silla", "fecha_estudio",
        "sede", "ciudad_registro", "elaboro_estudio",
    ]
    for key in estudio_field_keys:
        val = getattr(body, key, None)
        if val is not None:
            estudio_fields[key] = val

    # status_estudio mapped to estudio's status
    if body.status_estudio is not None:
        estudio_fields["status"] = body.status_estudio

    if "tuvo_silla_previa" in estudio_fields:
        estudio_fields["tuvo_silla_previa"] = int(estudio_fields["tuvo_silla_previa"])
        estudio_fields["como_obtuvo_silla"] = _resolve_como_obtuvo_silla(
            estudio_fields["tuvo_silla_previa"], estudio_fields.get("como_obtuvo_silla")
        )

    if estudio_fields:
        estudio_fields = _nullify_empty_strings(estudio_fields)
        set_clause = ", ".join(f"{k} = %s" for k in estudio_fields)
        values = list(estudio_fields.values())
        values.append(estudio["id"])
        db.execute(
            f"UPDATE estudios_socioeconomicos SET {set_clause}, updated_at = NOW() WHERE id = %s",
            values,
        )
        updated_estudio = True
        db.commit()

    # Build solicitud fields
    solicitud_fields = {}
    solicitud_field_keys = ["entidad_solicitante", "prioridad", "justificacion"]
    for key in solicitud_field_keys:
        val = getattr(body, key, None)
        if val is not None:
            solicitud_fields[key] = val

    if solicitud_fields:
        solicitud_fields = _nullify_empty_strings(solicitud_fields)
        set_clause = ", ".join(f"{k} = %s" for k in solicitud_fields)
        values = list(solicitud_fields.values())
        values.append(solicitud["id"])
        db.execute(
            f"UPDATE solicitudes_tecnicas SET {set_clause}, updated_at = NOW() WHERE id = %s",
            values,
        )
        updated_solicitud = True
        db.commit()

    return {
        "beneficiario_id": beneficiario_id,
        "estudio_id": estudio["id"],
        "estudio_updated": updated_estudio,
        "solicitud_id": solicitud["id"],
        "solicitud_updated": updated_solicitud,
    }


@router.delete("/admin/beneficiarios/{beneficiario_id}")
def eliminar_beneficiario_admin(
    beneficiario_id: int,
    db: Annotated[_DBAdapter, Depends(get_db)],
    _usuario: Annotated[CurrentUser, Depends(require_roles("admin"))],
) -> dict:
    """Hard delete a beneficiario and all associated records (cascade). Admin only."""
    _ensure_beneficiario(db, beneficiario_id)

    # Cascade delete order (children first):
    # 1. procesos_tecnicos_participantes (via procesos_tecnicos)
    # 2. procesos_tecnicos
    # 3. solicitudes_tecnicas
    # 4. estudios_socioeconomicos
    # 5. tutores
    # 6. beneficiarios

    deleted = {}

    # 1 & 2: Delete procesos_tecnicos_participantes + procesos_tecnicos
    procesos = db.execute(
        "SELECT id FROM procesos_tecnicos WHERE beneficiario_id = %s",
        (beneficiario_id,),
    ).fetchall()
    if procesos:
        proceso_ids = [p["id"] for p in procesos]
        placeholders = ", ".join("%s" for _ in proceso_ids)
        result = db.execute(
            f"DELETE FROM procesos_tecnicos_participantes WHERE proceso_tecnico_id IN ({placeholders})",
            tuple(proceso_ids),
        )
        deleted["procesos_tecnicos_participantes"] = len(proceso_ids)

        result2 = db.execute(
            f"DELETE FROM procesos_tecnicos WHERE id IN ({placeholders})",
            tuple(proceso_ids),
        )
        deleted["procesos_tecnicos"] = len(proceso_ids)

    # 3. solicitudes_tecnicas
    result = db.execute(
        "DELETE FROM solicitudes_tecnicas WHERE beneficiario_id = %s",
        (beneficiario_id,),
    )
    deleted["solicitudes_tecnicas"] = result._cur.rowcount

    # 4. estudios_socioeconomicos
    result = db.execute(
        "DELETE FROM estudios_socioeconomicos WHERE beneficiario_id = %s",
        (beneficiario_id,),
    )
    deleted["estudios_socioeconomicos"] = result._cur.rowcount

    # 5. tutores
    result = db.execute(
        "DELETE FROM tutores WHERE beneficiario_id = %s",
        (beneficiario_id,),
    )
    deleted["tutores"] = result._cur.rowcount

    # 6. beneficiarios
    result = db.execute(
        "DELETE FROM beneficiarios WHERE id = %s",
        (beneficiario_id,),
    )
    deleted["beneficiarios"] = result._cur.rowcount
    db.commit()

    return {
        "beneficiario_id": beneficiario_id,
        "deleted": True,
        "registros_eliminados": deleted,
        "total_eliminados": sum(deleted.values()),
    }
