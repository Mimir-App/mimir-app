use super::get_client;

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
