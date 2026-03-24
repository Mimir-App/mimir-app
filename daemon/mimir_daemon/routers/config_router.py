"""Router de configuracion e integraciones."""

import json
import logging

from fastapi import APIRouter, Request

from ..server_models import AppConfigRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/config")
async def get_config(request: Request) -> dict:
    """Devuelve la configuracion actual del daemon recibida desde Tauri."""
    app_config = request.app.state.app_config
    # No devolvemos tokens por seguridad
    safe_config = {
        k: v for k, v in app_config.items()
        if "token" not in k and "password" not in k and k != "ai_api_key"
    }
    safe_config["odoo_configured"] = bool(
        app_config.get("odoo_url") and app_config.get("odoo_token")
    )
    safe_config["gitlab_configured"] = bool(
        app_config.get("gitlab_url") and app_config.get("gitlab_token")
    )
    safe_config["github_configured"] = bool(
        app_config.get("github_token")
    )
    safe_config["ai_configured"] = bool(
        app_config.get("ai_provider", "none") != "none"
        and app_config.get("ai_api_key")
    )
    return safe_config


@router.put("/config")
async def update_config(request: Request, req: AppConfigRequest) -> dict:
    """Recibe configuracion desde Tauri y configura integraciones."""
    app_config = request.app.state.app_config
    registry = request.app.state.registry
    ai_service = request.app.state.ai_service
    source_registry = request.app.state.source_registry
    db = request.app.state.db

    config_data = req.model_dump()
    app_config.update(config_data)
    logger.info("Configuracion actualizada desde Tauri")

    # Configurar integracion Odoo si hay datos suficientes
    if req.odoo_url and req.odoo_token:
        try:
            if req.odoo_version == "v11":
                from ..integrations.odoo_v11 import OdooV11Client
                client = OdooV11Client(
                    url=req.odoo_url,
                    db=req.odoo_db,
                    username=req.odoo_username,
                    password=req.odoo_token,
                    timezone=config_data.get("timezone", "Europe/Madrid"),
                )
                auth_ok = await client.authenticate()
                if auth_ok:
                    registry.set_timesheet_client(client)
                    logger.info("Cliente Odoo v11 configurado: %s", req.odoo_url)
                else:
                    logger.warning("Autenticacion fallida con Odoo v11")
                    return {
                        "status": "partial",
                        "odoo": "auth_failed",
                        "message": "No se pudo autenticar con Odoo v11",
                    }
            else:
                from ..integrations.odoo_v16 import OdooV16Client
                client = OdooV16Client(
                    url=req.odoo_url,
                    db=req.odoo_db,
                    token=req.odoo_token,
                    timezone=config_data.get("timezone", "Europe/Madrid"),
                )
                auth_ok = await client.authenticate()
                if auth_ok:
                    registry.set_timesheet_client(client)
                    logger.info("Cliente Odoo v16 configurado: %s", req.odoo_url)
                else:
                    logger.warning("Autenticacion fallida con Odoo v16")
                    return {
                        "status": "partial",
                        "odoo": "auth_failed",
                        "message": "No se pudo autenticar con Odoo v16",
                    }
        except Exception as e:
            logger.error("Error configurando Odoo: %s", e)
            return {
                "status": "partial",
                "odoo": "error",
                "message": f"Error configurando Odoo: {e}",
            }

    # Configurar provider IA
    if ai_service and req.ai_provider != "none" and req.ai_api_key:
        try:
            from ..ai.service import AIService
            ai_service.provider = AIService.create_provider(req.ai_provider, req.ai_api_key)
            logger.info("Provider IA configurado: %s", req.ai_provider)
        except Exception as e:
            logger.error("Error configurando provider IA: %s", e)
    elif ai_service and req.ai_provider == "none":
        ai_service.provider = None
        logger.info("Provider IA desactivado")

    # Actualizar contexto de usuario en AIService
    if ai_service:
        ai_service.user_role = req.ai_user_role
        ai_service.user_context = req.ai_custom_context

    # Configurar GitLab source
    if req.gitlab_url and req.gitlab_token:
        try:
            from ..sources.gitlab import GitLabSource
            gitlab_source = GitLabSource(url=req.gitlab_url, token=req.gitlab_token)
            source_registry.register_vcs("gitlab", gitlab_source)
            logger.info("GitLab source configurado: %s", req.gitlab_url)
        except Exception as e:
            logger.error("Error configurando GitLab: %s", e)
    else:
        source_registry.unregister_vcs("gitlab")

    # Configurar GitHub source
    if req.github_token:
        try:
            from ..sources.github import GitHubSource
            github_source = GitHubSource(token=req.github_token)
            source_registry.register_vcs("github", github_source)
            logger.info("GitHub source configurado")
        except Exception as e:
            logger.error("Error configurando GitHub: %s", e)
    else:
        source_registry.unregister_vcs("github")

    # Guardar configuracion en preferences cache de la DB
    try:
        safe = {k: v for k, v in config_data.items() if "token" not in k and "password" not in k}
        await db.set_preference("app_config", json.dumps(safe, ensure_ascii=False))
    except Exception as e:
        logger.error("Error guardando config en cache: %s", e)

    return {"status": "ok"}


@router.get("/config/integration-status")
async def get_integration_status(request: Request) -> dict:
    """Devuelve el estado de las integraciones configuradas."""
    registry = request.app.state.registry
    source_registry = request.app.state.source_registry
    return {
        "odoo": {
            "configured": registry.timesheet is not None,
            "client_type": type(registry.timesheet).__name__ if registry.timesheet else None,
        },
        "gitlab": {
            "configured": source_registry.has_source("gitlab"),
        },
        "github": {
            "configured": source_registry.has_source("github"),
        },
    }
