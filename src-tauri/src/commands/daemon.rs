use crate::clients::daemon_client::DaemonClient;
use crate::commands::config::{get_config, AppConfig};
use crate::models::block::{ActivityBlock, BlockUpdate, DaemonStatus};
use crate::models::timesheet::{OdooProject, OdooTask, TimesheetEntry};

fn get_client() -> DaemonClient {
    let port = match get_config() {
        Ok(config) => config.daemon_port,
        Err(_) => 9477,
    };
    DaemonClient::new(port)
}

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
    let client = DaemonClient::new(9476);
    Ok(client.health_check().await)
}

#[tauri::command]
pub async fn set_daemon_mode(mode: String) -> Result<(), String> {
    #[derive(serde::Serialize)]
    struct ModeReq { mode: String }
    get_client().post_empty("/mode", &ModeReq { mode }).await
}

#[tauri::command]
pub async fn get_blocks(date: String) -> Result<Vec<ActivityBlock>, String> {
    get_client().get(&format!("/blocks?date={}", date)).await
}

#[tauri::command]
pub async fn confirm_block(block_id: i64) -> Result<(), String> {
    get_client().post_empty(&format!("/blocks/{}/confirm", block_id), &()).await
}

#[tauri::command]
pub async fn update_block(block_id: i64, updates: BlockUpdate) -> Result<(), String> {
    get_client().put(&format!("/blocks/{}", block_id), &updates).await
}

#[tauri::command]
pub async fn delete_block(block_id: i64) -> Result<(), String> {
    get_client().delete(&format!("/blocks/{}", block_id)).await
}

#[tauri::command]
pub async fn sync_blocks_to_odoo(block_ids: Vec<i64>) -> Result<(), String> {
    #[derive(serde::Serialize)]
    struct SyncReq { block_ids: Vec<i64> }
    get_client().post_empty("/blocks/sync", &SyncReq { block_ids }).await
}

#[tauri::command]
pub async fn retry_sync_block(block_id: i64) -> Result<(), String> {
    get_client()
        .post_empty(&format!("/blocks/{}/retry", block_id), &())
        .await
}

#[tauri::command]
pub async fn get_odoo_projects() -> Result<Vec<OdooProject>, String> {
    get_client().get("/odoo/projects").await
}

#[tauri::command]
pub async fn get_odoo_tasks(project_id: i64) -> Result<Vec<OdooTask>, String> {
    get_client().get(&format!("/odoo/tasks/{}", project_id)).await
}

#[tauri::command]
pub async fn get_timesheet_entries(
    date_from: String,
    date_to: String,
) -> Result<Vec<TimesheetEntry>, String> {
    get_client()
        .get(&format!("/odoo/entries?from={}&to={}", date_from, date_to))
        .await
}

#[tauri::command]
pub async fn get_issues() -> Result<Vec<serde_json::Value>, String> {
    get_client().get("/gitlab/issues").await
}

#[tauri::command]
pub async fn get_merge_requests() -> Result<Vec<serde_json::Value>, String> {
    get_client().get("/gitlab/merge_requests").await
}

// --- Signals ---

#[tauri::command]
pub async fn get_signals(date: Option<String>, block_id: Option<i64>) -> Result<Vec<serde_json::Value>, String> {
    let mut params = Vec::new();
    if let Some(d) = date { params.push(format!("date={}", d)); }
    if let Some(b) = block_id { params.push(format!("block_id={}", b)); }
    let query = if params.is_empty() { String::new() } else { format!("?{}", params.join("&")) };
    get_client().get(&format!("/signals{}", query)).await
}

#[tauri::command]
pub async fn split_block(block_id: i64, signal_id: i64) -> Result<serde_json::Value, String> {
    get_client()
        .post::<serde_json::Value, _>(
            &format!("/blocks/{}/split?signal_id={}", block_id, signal_id),
            &(),
        )
        .await
}

#[tauri::command]
pub async fn merge_blocks(block_ids: Vec<i64>) -> Result<serde_json::Value, String> {
    #[derive(serde::Serialize)]
    struct MergeReq { block_ids: Vec<i64> }
    get_client()
        .post::<serde_json::Value, _>("/blocks/merge", &MergeReq { block_ids })
        .await
}

// --- Google Calendar ---

#[tauri::command]
pub async fn get_google_auth_url() -> Result<serde_json::Value, String> {
    get_client().get("/google/calendar/auth-url").await
}

#[tauri::command]
pub async fn get_google_calendar_status() -> Result<serde_json::Value, String> {
    get_client().get("/google/calendar/status").await
}

#[tauri::command]
pub async fn disconnect_google_calendar() -> Result<serde_json::Value, String> {
    get_client()
        .post::<serde_json::Value, _>("/google/calendar/disconnect", &())
        .await
}

// --- Attendance ---

#[tauri::command]
pub async fn get_attendance_today() -> Result<serde_json::Value, String> {
    get_client().get("/odoo/attendance/today").await
}

#[tauri::command]
pub async fn attendance_check_in() -> Result<serde_json::Value, String> {
    get_client()
        .post::<serde_json::Value, _>("/odoo/attendance/checkin", &())
        .await
}

#[tauri::command]
pub async fn attendance_check_out(attendance_id: i64) -> Result<serde_json::Value, String> {
    get_client()
        .post::<serde_json::Value, _>(
            &format!("/odoo/attendance/{}/checkout", attendance_id),
            &(),
        )
        .await
}

/// Recupera un token del keyring de forma segura.
fn read_keyring_token(service: &str) -> String {
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
        ai_provider: config.ai_provider,
        ai_api_key,
        ai_user_role: config.ai_user_role,
        ai_custom_context: config.ai_custom_context,
    };

    get_client()
        .put_json::<serde_json::Value, _>("/config", &payload)
        .await
}

/// Genera o regenera la descripción IA de un bloque.
#[tauri::command]
pub async fn generate_block_description(block_id: i64) -> Result<serde_json::Value, String> {
    get_client()
        .post::<serde_json::Value, _>(
            &format!("/blocks/{}/generate-description", block_id),
            &(),
        )
        .await
}

/// Obtiene el estado de las integraciones del daemon.
#[tauri::command]
pub async fn get_integration_status() -> Result<serde_json::Value, String> {
    get_client().get("/config/integration-status").await
}

// --- GitLab Issues (preferences, search, followed, labels, notes) ---

#[tauri::command]
pub async fn get_issue_preferences() -> Result<serde_json::Value, String> {
    get_client().get("/gitlab/issues/preferences").await
}

#[tauri::command]
pub async fn update_issue_preferences(issue_id: u64, body: serde_json::Value) -> Result<serde_json::Value, String> {
    get_client().put_json(&format!("/gitlab/issues/{}/preferences", issue_id), &body).await
}

#[tauri::command]
pub async fn search_gitlab_issues(q: String) -> Result<serde_json::Value, String> {
    get_client().get(&format!("/gitlab/issues/search?q={}", q)).await
}

#[tauri::command]
pub async fn get_followed_issues() -> Result<serde_json::Value, String> {
    get_client().get("/gitlab/issues/followed").await
}

#[tauri::command]
pub async fn get_gitlab_labels() -> Result<serde_json::Value, String> {
    get_client().get("/gitlab/labels").await
}

#[tauri::command]
pub async fn get_issue_notes(project_id: String, issue_iid: u64, per_page: u32) -> Result<serde_json::Value, String> {
    get_client().get(&format!("/gitlab/issues/{}/{}/notes?per_page={}", project_id, issue_iid, per_page)).await
}

// --- Odoo entries ---

#[tauri::command]
pub async fn update_timesheet_entry(entry_id: u64, body: serde_json::Value) -> Result<serde_json::Value, String> {
    get_client().put_json(&format!("/odoo/entries/{}", entry_id), &body).await
}
