"""Router de GitHub OAuth Device Flow."""

import logging

import httpx
from fastapi import APIRouter, Body, Request

logger = logging.getLogger(__name__)

router = APIRouter()

_GITHUB_OAUTH_CLIENT_ID = "Ov23liSNCnplhPIkY2kx"


@router.post("/github/oauth/start")
async def github_oauth_start() -> dict:
    """Inicia el flujo OAuth Device Flow de GitHub."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://github.com/login/device/code",
                data={
                    "client_id": _GITHUB_OAUTH_CLIENT_ID,
                    "scope": "repo read:org notifications",
                },
                headers={"Accept": "application/json"},
            )
            if resp.status_code != 200:
                logger.error("GitHub device code error: %s", resp.text)
                return {"error": f"GitHub respondio {resp.status_code}"}
            data = resp.json()
            return {
                "device_code": data["device_code"],
                "user_code": data["user_code"],
                "verification_uri": data["verification_uri"],
                "expires_in": data.get("expires_in", 900),
                "interval": data.get("interval", 5),
            }
    except Exception as e:
        logger.error("Error iniciando GitHub OAuth: %s", e)
        return {"error": str(e)}


@router.post("/github/oauth/poll")
async def github_oauth_poll(request: Request, body: dict = Body(...)) -> dict:
    """Hace polling para obtener el token OAuth de GitHub."""
    app_config = request.app.state.app_config
    source_registry = request.app.state.source_registry
    device_code = body.get("device_code")
    if not device_code:
        return {"error": "device_code requerido"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": _GITHUB_OAUTH_CLIENT_ID,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                headers={"Accept": "application/json"},
            )
            data = resp.json()
            if "access_token" in data:
                # Registrar el source con el nuevo token
                token = data["access_token"]
                app_config["github_token"] = token
                from ..sources.github import GitHubSource
                github_source = GitHubSource(token=token)
                source_registry.register_vcs("github", github_source)
                logger.info("GitHub OAuth completado — source registrado")
                return {"status": "complete", "access_token": token}
            error = data.get("error", "unknown")
            if error == "authorization_pending":
                return {"status": "pending"}
            if error == "slow_down":
                return {"status": "slow_down", "interval": data.get("interval", 10)}
            if error == "expired_token":
                return {"status": "expired"}
            return {"status": "error", "error": data.get("error_description", error)}
    except Exception as e:
        logger.error("Error polling GitHub OAuth: %s", e)
        return {"status": "error", "error": str(e)}
