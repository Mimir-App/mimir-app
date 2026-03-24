mod blocks;
mod odoo;
mod vcs;
mod config_cmd;
mod google;
mod notifications;
mod context;
mod items;
mod github_oauth;

// Shared helpers
use crate::clients::daemon_client::DaemonClient;
use crate::commands::config::get_config;

pub(crate) fn get_client() -> DaemonClient {
    let port = match get_config() {
        Ok(config) => config.daemon_port,
        Err(_) => 9477,
    };
    DaemonClient::new(port)
}

pub(crate) fn get_capture_client() -> DaemonClient {
    DaemonClient::new(9476)
}

// Health endpoints (stay in mod.rs since they use both clients)
use crate::models::block::DaemonStatus;

#[tauri::command]
pub async fn get_daemon_status() -> Result<DaemonStatus, String> {
    get_client().get("/status").await
}

#[tauri::command]
pub async fn daemon_health_check() -> Result<bool, String> {
    Ok(get_client().health_check().await)
}

#[tauri::command]
pub async fn capture_health_check() -> Result<bool, String> {
    Ok(get_capture_client().health_check().await)
}

#[tauri::command]
pub async fn get_capture_health() -> Result<serde_json::Value, String> {
    get_capture_client().get("/health").await
}

#[tauri::command]
pub async fn set_daemon_mode(mode: String) -> Result<(), String> {
    #[derive(serde::Serialize)]
    struct ModeReq { mode: String }
    get_client().post_empty("/mode", &ModeReq { mode }).await
}

// Re-export all submodule commands
pub use blocks::*;
pub use odoo::*;
pub use vcs::*;
pub use config_cmd::*;
pub use google::*;
pub use notifications::*;
pub use context::*;
pub use items::*;
pub use github_oauth::*;
