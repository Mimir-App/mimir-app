use crate::clients::daemon_client::DaemonClient;
use crate::models::block::{ActivityBlock, BlockUpdate, DaemonStatus};
use crate::models::timesheet::{OdooProject, OdooTask, TimesheetEntry};
use crate::models::issue::GitLabIssue;
use crate::models::merge_request::GitLabMergeRequest;
fn get_client() -> DaemonClient {
    // TODO: leer puerto de config
    DaemonClient::new(9477)
}

#[tauri::command]
pub async fn get_daemon_status() -> Result<DaemonStatus, String> {
    get_client().get("/status").await
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
    get_client().post_empty(&format!("/blocks/{}/update", block_id), &updates).await
}

#[tauri::command]
pub async fn sync_blocks_to_odoo(block_ids: Vec<i64>) -> Result<(), String> {
    #[derive(serde::Serialize)]
    struct SyncReq { block_ids: Vec<i64> }
    get_client().post_empty("/blocks/sync", &SyncReq { block_ids }).await
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
pub async fn get_issues() -> Result<Vec<GitLabIssue>, String> {
    get_client().get("/gitlab/issues").await
}

#[tauri::command]
pub async fn get_merge_requests() -> Result<Vec<GitLabMergeRequest>, String> {
    get_client().get("/gitlab/merge_requests").await
}
