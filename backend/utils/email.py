"""
Email delivery via the Resend REST API.

Environment variables:
  RESEND_API_KEY   — Bearer token for https://api.resend.com (required to send).
  EMAIL_FROM       — Sender address (default "onboarding@resend.dev" for dev).
  APP_BASE_URL     — Base URL used to build activation/reset links in emails
                     (e.g. "https://sillas.example.com"). If unset the links are
                     relative ("/set-password.html?token=..."); production MUST
                     set this so email clients resolve absolute URLs.

All copy is in Spanish (neutral/professional) — the platform is Spanish.

Design note: callers treat email delivery as best-effort (fail-open). They
catch EmailDeliveryError, log a warning, and keep the created user/token so an
admin can resend the invitation. Raw tokens appear only in the link and are
never logged or persisted (only their sha256 hash is stored).
"""

import os

import httpx

_RESEND_ENDPOINT = "https://api.resend.com/emails"
_TIMEOUT_SECONDS = 10.0
_DEFAULT_FROM = "onboarding@resend.dev"


class EmailDeliveryError(Exception):
    """Raised when Resend returns a non-2xx status or the request times out."""


def _resend_post(to: str, subject: str, html: str) -> None:
    """POST a single email to Resend. Raises EmailDeliveryError on failure."""
    api_key = os.environ["RESEND_API_KEY"]
    from_addr = os.environ.get("EMAIL_FROM", _DEFAULT_FROM)
    try:
        resp = httpx.post(
            _RESEND_ENDPOINT,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": from_addr,
                "to": [to],
                "subject": subject,
                "html": html,
            },
            timeout=_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
    except httpx.TimeoutException as exc:
        raise EmailDeliveryError("Resend request timed out") from exc
    except httpx.HTTPStatusError as exc:
        raise EmailDeliveryError(
            f"Resend returned {exc.response.status_code}"
        ) from exc
    except httpx.HTTPError as exc:  # transport/connection errors
        raise EmailDeliveryError(f"Resend request failed: {exc}") from exc


def _base_url() -> str:
    """Return APP_BASE_URL without a trailing slash (empty when unset)."""
    return os.environ.get("APP_BASE_URL", "").rstrip("/")


def send_invite(to_email: str, raw_token: str) -> None:
    """Send the account-activation (invite) email. Valid for 72 hours."""
    link = f"{_base_url()}/set-password.html?token={raw_token}"
    html = f"""
    <p>Tu cuenta en <strong>Ecosistema VIDA UG</strong> ha sido creada.</p>
    <p>Hacé clic en el siguiente enlace para establecer tu contraseña y activar
    tu cuenta (este enlace expira en 72 horas):</p>
    <p><a href="{link}">Activar mi cuenta</a></p>
    <p>Si no esperabas este mensaje, podés ignorarlo.</p>
    """
    _resend_post(to_email, "Bienvenido/a — Activá tu cuenta", html)


def send_reset(to_email: str, raw_token: str) -> None:
    """Send the password-reset email. Valid for 1 hour."""
    link = f"{_base_url()}/reset-password.html?token={raw_token}"
    html = f"""
    <p>Recibimos una solicitud para restablecer la contraseña de tu cuenta en
    <strong>Ecosistema VIDA UG</strong>.</p>
    <p>Hacé clic en el siguiente enlace para crear una nueva contraseña
    (este enlace expira en 1 hora):</p>
    <p><a href="{link}">Restablecer mi contraseña</a></p>
    <p>Si no solicitaste este cambio, podés ignorarlo.</p>
    """
    _resend_post(to_email, "Recuperación de contraseña", html)
