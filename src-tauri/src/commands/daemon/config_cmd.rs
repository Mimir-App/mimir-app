use crate::commands::config::AppConfig;

use super::get_client;

/// Recupera un token del keyring de forma segura.
pub(crate) fn read_keyring_token(service: &str) -> String {
    match keyring::Entry::new("mimir", service) {
        Ok(entry) => match entry.get_password() {
            Ok(t) => t,
            Err(_) => String::new(),
        },
        Err(_) => String::new(),
    }
}

/// Envia la configuracion de integraciones al daemon.
/// Recupera tokens del keyring y los envia junto con la config.
#[tauri::command]
pub async fn push_config_to_daemon(config: AppConfig) -> Result<serde_json::Value, String> {
    // Recuperar tokens del keyring (operacion sincrona)
    let odoo_token = read_keyring_token("odoo");
    let gitlab_token = read_keyring_token("gitlab");
    let github_token = read_keyring_token("github");
    let ai_api_key = read_keyring_token("ai");

    #[derive(serde::Serialize)]
    struct DaemonConfigPayload {
        odoo_url: String,
        odoo_version: String,
        odoo_db: String,
        odoo_username: String,
        odoo_token: String,
        gitlab_url: String,
        gitlab_token: String,
        github_token: String,
        ai_provider: String,
        ai_api_key: String,
        ai_user_role: String,
        ai_custom_context: String,
    }

    let payload = DaemonConfigPayload {
        odoo_url: config.odoo_url,
        odoo_version: config.odoo_version,
        odoo_db: config.odoo_db,
        odoo_username: config.odoo_username,
        odoo_token,
        gitlab_url: config.gitlab_url,
        gitlab_token,
        github_token,
        ai_provider: config.ai_provider,
        ai_api_key,
        ai_user_role: config.ai_user_role,
        ai_custom_context: config.ai_custom_context,
    };

    get_client()
        .put_json::<serde_json::Value, _>("/config", &payload)
        .await
}

/// Obtiene el estado de las integraciones del daemon.
#[tauri::command]
pub async fn get_integration_status() -> Result<serde_json::Value, String> {
    get_client().get("/config/integration-status").await
}

/// Detecta navegadores instalados en el sistema.
#[tauri::command]
pub async fn get_detected_browsers() -> Result<serde_json::Value, String> {
    get_client().get("/config/detected-browsers").await
}
