# Design: Mejoras Visuales

## Technical Approach
Implement the visual changes matching the provided references "tal cual" using Tailwind CSS via the existing CDN setup. The redesign will maintain the current JWT auth flow while introducing a two-column responsive layout for login and data-rich UI updates for the capturista profile. Backend endpoints will be extended to supply the missing statistics, avatar data, and filtering logic without breaking existing consumers.

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|---|---|---|---|
| **Video Asset Hosting** | Serve static video from `front/assets/video/` | Load directly from `REFERENCIAS/` or external CDN | `REFERENCIAS` is external to the webroot. Local assets ensure stable paths. |
| **Profile Avatar Storage** | Add `avatar_url` to `usuarios` table | Use hardcoded UI fallback only | Reference shows an avatar; allowing users to have an avatar future-proofs the profile. |
| **Heatmap Filtering** | Pass `?year=YYYY` query param to `/api/me/heatmap` | Filter 365-day payload on the client | Server-side filtering scales better for multi-year usage. |
| **Tailwind Strategy** | Standard utility classes, avoid `hex` and `var()` in `className` | Custom CSS or inline styles | Adheres to project `tailwind-4` skill rules and keeps styling consistent. |

## Data Flow

    Login View ──→ Auth API (/api/auth/login) ──→ JWT ──→ Profile View
                                                             │
    Profile View ──→ GET /api/me/perfil ───────────→ Stats & Avatar
                 ├─→ GET /api/me/heatmap?year=Y ───→ Activity Data
                 └─→ GET /api/me/beneficiarios ────→ Search & List

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `front/login.html` | Modify | Two-column layout (form + video). Video hidden on mobile. |
| `front/Capturista-view/perfil-capturista.html` | Modify | Update cards, counters (Pendientes), avatar, search bar. |
| `front/assets/video/VIDEOLOGIN.mp4` | Create | Copy from `REFERENCIAS/VIDEOLOGIN.mp4`. |
| `backend/routers/perfiles.py` | Modify | Add `pendientes`, `last_activity_date`, `avatar_url` to profile payload. Add year filtering to heatmap. Add search/status filters to beneficiaries list. |
| `backend/init_db.py` | Modify | Add `avatar_url` column to `usuarios` table initialization. |

## Interfaces / Contracts

```python
# Updated /api/me/perfil response
class PerfilResponse(BaseModel):
    nombre: str
    rol: str
    avatar_url: Optional[str]
    total_capturas: int
    this_month: int
    pendientes: int
    last_activity_date: Optional[datetime]

# Updated /api/me/heatmap params
# GET /api/me/heatmap?year=2026
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| **Unit (API)** | Profile Stats & Filters | Test `perfiles.py` endpoints for new parameters (`year`, search strings). |
| **E2E (UI)** | Login Layout & Video | Verify two-column layout on desktop, stacked on mobile. Ensure form submits correctly. |
| **E2E (UI)** | Profile Interactivity | Verify heatmap updates on year change and search filters beneficiaries accurately. |

## Chained PR Strategy (`force-chained`)

1. **PR 1: Backend API Extensions & DB Schema**: Add `avatar_url` to schema. Extend `/api/me/perfil`, `/api/me/heatmap`, and `/api/me/beneficiarios`.
2. **PR 2: Asset Prep & Login Redesign**: Copy video to assets. Rewrite `login.html` layout.
3. **PR 3: Capturista Profile UI**: Redesign `perfil-capturista.html` and connect new API data points (pendientes, year filter, search).

## Migration / Rollout
Run `init_db.py` (or equivalent migration script) to alter the `usuarios` table and append the `avatar_url` column before deploying backend updates.

## Open Questions
- None.
