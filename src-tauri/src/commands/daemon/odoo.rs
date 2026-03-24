use crate::models::timesheet::{OdooProject, OdooTask, TimesheetEntry};

use super::get_client;

#[tauri::command]
pub async fn get_odoo_projects() -> Result<Vec<OdooProject>, String> {
    get_client().get("/odoo/projects").await
}

#[tauri::command]
pub async fn get_odoo_tasks(project_id: i64) -> Result<Vec<OdooTask>, String> {
    get_client().get(&format!("/odoo/tasks/{}", project_id)).await
}

#[tauri::command]
pub async fn search_odoo_tasks(query: String, limit: i64) -> Result<Vec<OdooTask>, String> {
    get_client()
        .get(&format!(
            "/odoo/tasks/search?query={}&limit={}",
            urlencoding::encode(&query),
            limit
        ))
        .await
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

// --- Odoo entries ---

#[tauri::command]
pub async fn update_timesheet_entry(entry_id: u64, body: serde_json::Value) -> Result<serde_json::Value, String> {
    get_client().put_json(&format!("/odoo/entries/{}", entry_id), &body).await
}
