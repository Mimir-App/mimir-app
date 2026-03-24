use super::get_client;

#[tauri::command]
pub async fn get_notifications(unread_only: bool) -> Result<serde_json::Value, String> {
    get_client().get(&format!("/notifications?unread_only={}", unread_only)).await
}

#[tauri::command]
pub async fn get_notification_count() -> Result<serde_json::Value, String> {
    get_client().get("/notifications/count").await
}

#[tauri::command]
pub async fn mark_notification_read(notification_id: u64) -> Result<serde_json::Value, String> {
    get_client().put_json(&format!("/notifications/{}/read", notification_id), &serde_json::json!({})).await
}

#[tauri::command]
pub async fn mark_all_notifications_read() -> Result<serde_json::Value, String> {
    get_client().put_json("/notifications/read-all", &serde_json::json!({})).await
}
