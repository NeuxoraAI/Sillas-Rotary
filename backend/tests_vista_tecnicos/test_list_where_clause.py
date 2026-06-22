"""RED — Tests for _build_list_where_clause with advanced filters.

These tests exercise PHASE 1 (filter extensions) before the production code
supports them. They MUST fail initially.
"""

# ruff: noqa: ANN201


def _call(**kwargs) -> tuple[str, list]:
    """Wrapper to import and call _build_list_where_clause."""
    from routers.tecnica import _build_list_where_clause
    return _build_list_where_clause(**kwargs)


# ── Existing params still work ───────────────────────────────────────────────

def test_existing_q_param():
    where, params = _call(q="ana", sede=None)
    assert "b.nombre ILIKE" in where
    assert "%ana%" in params


def test_existing_sede_param():
    where, params = _call(q=None, sede="León")
    assert "COALESCE(e.sede, '') = %s" in where
    assert "León" in params


# ── NEW: pais_id param ───────────────────────────────────────────────────────

def test_pais_id_filter():
    """GIVEN pais_id=5 WHEN called THEN SQL has b.region_id IN (SELECT ...) clause."""
    where, params = _call(
        q=None, sede=None,
        pais_id=5,
    )
    assert "pais_id" in where or "b.region_id IN" in where
    assert 5 in params


# ── NEW: region_id param ─────────────────────────────────────────────────────

def test_region_id_filter():
    """GIVEN region_id=12 WHEN called THEN exact match on b.region_id."""
    where, params = _call(
        q=None, sede=None,
        region_id=12,
    )
    assert "b.region_id" in where
    assert 12 in params


# ── NEW: ciudad param ─────────────────────────────────────────────────────────

def test_ciudad_filter():
    """GIVEN ciudad='León' WHEN called THEN ILIKE on b.ciudad."""
    where, params = _call(
        q=None, sede=None,
        ciudad="León",
    )
    assert "b.ciudad ILIKE" in where
    assert "%León%" in params


# ── NEW: peso_kg range filter ────────────────────────────────────────────────

def test_peso_kg_min_filter():
    """GIVEN peso_kg_min=50.0 WHEN called THEN st.peso_kg >= %s."""
    where, params = _call(
        q=None, sede=None,
        peso_kg_min=50.0,
    )
    assert "st.peso_kg" in where
    assert 50.0 in params


def test_peso_kg_max_filter():
    """GIVEN peso_kg_max=80.0 WHEN called THEN st.peso_kg <= %s."""
    where, params = _call(
        q=None, sede=None,
        peso_kg_max=80.0,
    )
    assert "st.peso_kg" in where
    assert 80.0 in params


def test_peso_kg_range_filter():
    """GIVEN both min and max WHEN called THEN range clause with both."""
    where, params = _call(
        q=None, sede=None,
        peso_kg_min=50.0, peso_kg_max=80.0,
    )
    assert "st.peso_kg" in where
    assert "AND" in where or "BETWEEN" in where
    assert 50.0 in params
    assert 80.0 in params


# ── NEW: altura_in range filter ──────────────────────────────────────────────

def test_altura_in_min_filter():
    where, params = _call(
        q=None, sede=None,
        altura_in_min=60.0,
    )
    assert "st.altura_total_in" in where
    assert 60.0 in params


def test_altura_in_max_filter():
    where, params = _call(
        q=None, sede=None,
        altura_in_max=70.0,
    )
    assert "st.altura_total_in" in where
    assert 70.0 in params


# ── NEW: tiene_foto param ────────────────────────────────────────────────────

def test_tiene_foto_true_filter():
    """GIVEN tiene_foto=True WHEN called THEN foto_url IS NOT NULL."""
    where, params = _call(
        q=None, sede=None,
        tiene_foto=True,
    )
    assert "foto_url IS NOT NULL" in where


def test_tiene_foto_false_filter():
    """GIVEN tiene_foto=False WHEN called THEN foto_url IS NULL."""
    where, params = _call(
        q=None, sede=None,
        tiene_foto=False,
    )
    assert "foto_url IS NULL" in where


# ── Task 1.3: Range validation ────────────────────────────────────────────────

def test_invalid_peso_range_raises_422():
    """GIVEN peso_kg_min=80 > peso_kg_max=50 WHEN called THEN 422 invalid_filter."""
    from fastapi import HTTPException
    try:
        _call(
            q=None, sede=None,
            peso_kg_min=80.0, peso_kg_max=50.0,
        )
        assert False, "Should have raised HTTPException 422"
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail["type"] == "invalid_filter"


def test_invalid_altura_range_raises_422():
    """GIVEN altura_in_min=70 > altura_in_max=60 WHEN called THEN 422 invalid_filter."""
    from fastapi import HTTPException
    try:
        _call(
            q=None, sede=None,
            altura_in_min=70.0, altura_in_max=60.0,
        )
        assert False, "Should have raised HTTPException 422"
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail["type"] == "invalid_filter"


def test_valid_range_does_not_raise():
    """GIVEN min <= max WHEN called THEN no exception."""
    result = _call(
        q=None, sede=None,
        peso_kg_min=50.0, peso_kg_max=80.0,
        altura_in_min=60.0, altura_in_max=70.0,
    )
    assert result is not None


# ── Task 1.4: Extended q search ──────────────────────────────────────────────

def test_q_matches_ciudad():
    """GIVEN q='León' WHEN called THEN WHERE includes b.ciudad ILIKE."""
    where, params = _call(q="León", sede=None)
    assert "b.ciudad ILIKE" in where
    assert "%León%" in params


def test_q_matches_region_nombre():
    """GIVEN q='Guanajuato' WHEN called THEN WHERE includes r.nombre ILIKE."""
    where, params = _call(q="Guanajuato", sede=None)
    assert "r.nombre ILIKE" in where
    assert "%Guanajuato%" in params


def test_q_matches_pais_nombre():
    """GIVEN q='México' WHEN called THEN WHERE includes p.nombre ILIKE."""
    where, params = _call(q="México", sede=None)
    assert "p.nombre ILIKE" in where
    assert "%México%" in params
