use super::get_client;

#[tauri::command]
pub async fn github_oauth_start() -> Result<serde_json::Value, String> {
    get_client().post("/github/oauth/start", &serde_json::json!({})).await
}

#[tauri::command]
pub async fn github_oauth_poll(body: serde_json::Value) -> Result<serde_json::Value, String> {
    get_client().post("/github/oauth/poll", &body).await
}
