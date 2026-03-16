"""Integración con Google Calendar via OAuth2.

Permite consultar eventos del calendario para enriquecer señales
con información de reuniones programadas.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

SCOPES = "https://www.googleapis.com/auth/calendar.readonly"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
CALENDAR_API = "https://www.googleapis.com/calendar/v3"

DEFAULT_TOKEN_PATH = Path.home() / ".config" / "mimir" / "google_tokens.json"


class GoogleCalendarClient:
    """Cliente de Google Calendar con OAuth2."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_path: str | Path = DEFAULT_TOKEN_PATH,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_path = Path(token_path)
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expiry: datetime | None = None
        self._http = httpx.AsyncClient(timeout=10)
        self._load_tokens()

    def _load_tokens(self) -> None:
        """Carga tokens guardados del disco."""
        if self._token_path.exists():
            try:
                data = json.loads(self._token_path.read_text(encoding="utf-8"))
                self._access_token = data.get("access_token")
                self._refresh_token = data.get("refresh_token")
                expiry = data.get("token_expiry")
                if expiry:
                    self._token_expiry = datetime.fromisoformat(expiry)
                logger.info("Tokens de Google Calendar cargados")
            except Exception as e:
                logger.warning("Error cargando tokens de Google Calendar: %s", e)

    def _save_tokens(self) -> None:
        """Guarda tokens al disco."""
        self._token_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
            "token_expiry": self._token_expiry.isoformat() if self._token_expiry else None,
        }
        self._token_path.write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )

    @property
    def is_configured(self) -> bool:
        """Indica si hay tokens disponibles."""
        return self._refresh_token is not None

    def get_auth_url(self, redirect_uri: str = "http://127.0.0.1:9477/oauth/google/callback") -> str:
        """Genera la URL de autorizacion OAuth2."""
        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": SCOPES,
            "access_type": "offline",
            "prompt": "consent",
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{AUTH_URL}?{query}"

    async def exchange_code(
        self, code: str, redirect_uri: str = "http://127.0.0.1:9477/oauth/google/callback"
    ) -> bool:
        """Intercambia el codigo de autorizacion por tokens."""
        try:
            resp = await self._http.post(TOKEN_URL, data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            })
            if resp.status_code != 200:
                logger.error("Error intercambiando codigo OAuth: %s", resp.text)
                return False

            data = resp.json()
            self._access_token = data["access_token"]
            self._refresh_token = data.get("refresh_token", self._refresh_token)
            expires_in = data.get("expires_in", 3600)
            self._token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            self._save_tokens()
            logger.info("Autorizacion de Google Calendar completada")
            return True
        except Exception as e:
            logger.error("Error en intercambio OAuth: %s", e)
            return False

    async def _ensure_valid_token(self) -> bool:
        """Refresca el token si ha expirado."""
        if not self._refresh_token:
            return False

        if self._access_token and self._token_expiry:
            if datetime.now(timezone.utc) < self._token_expiry - timedelta(minutes=5):
                return True

        try:
            resp = await self._http.post(TOKEN_URL, data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token",
            })
            if resp.status_code != 200:
                logger.error("Error refrescando token: %s", resp.text)
                return False

            data = resp.json()
            self._access_token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            self._token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            self._save_tokens()
            return True
        except Exception as e:
            logger.error("Error refrescando token de Google: %s", e)
            return False

    async def get_current_event(self) -> dict | None:
        """Obtiene el evento activo en este momento (si hay alguno).

        Devuelve dict con: summary, start, end, attendees, meet_link, o None.
        """
        if not await self._ensure_valid_token():
            return None

        now = datetime.now(timezone.utc)
        time_min = now.isoformat()
        time_max = (now + timedelta(minutes=1)).isoformat()

        try:
            resp = await self._http.get(
                f"{CALENDAR_API}/calendars/primary/events",
                headers={"Authorization": f"Bearer {self._access_token}"},
                params={
                    "timeMin": time_min,
                    "timeMax": time_max,
                    "singleEvents": "true",
                    "orderBy": "startTime",
                    "maxResults": "1",
                },
            )
            if resp.status_code != 200:
                logger.debug("Error consultando calendario: %s", resp.status_code)
                return None

            data = resp.json()
            items = data.get("items", [])
            if not items:
                return None

            event = items[0]
            # Solo eventos aceptados o sin respuesta (no rechazados)
            attendees = event.get("attendees", [])
            my_status = "accepted"
            for a in attendees:
                if a.get("self"):
                    my_status = a.get("responseStatus", "accepted")
                    break

            if my_status == "declined":
                return None

            # Extraer meet link
            meet_link = None
            conference = event.get("conferenceData", {})
            entry_points = conference.get("entryPoints", [])
            for ep in entry_points:
                if ep.get("entryPointType") == "video":
                    meet_link = ep.get("uri")
                    break

            return {
                "summary": event.get("summary", "Sin titulo"),
                "start": event.get("start", {}).get("dateTime", ""),
                "end": event.get("end", {}).get("dateTime", ""),
                "attendees": [
                    a.get("email", "") for a in attendees if not a.get("self")
                ],
                "meet_link": meet_link,
                "is_meeting": len(attendees) > 1 or meet_link is not None,
            }
        except Exception as e:
            logger.debug("Error obteniendo evento actual: %s", e)
            return None

    async def disconnect(self) -> None:
        """Elimina tokens y desconecta."""
        self._access_token = None
        self._refresh_token = None
        self._token_expiry = None
        if self._token_path.exists():
            self._token_path.unlink()
        logger.info("Google Calendar desconectado")

    async def close(self) -> None:
        """Cierra el cliente HTTP."""
        await self._http.aclose()
