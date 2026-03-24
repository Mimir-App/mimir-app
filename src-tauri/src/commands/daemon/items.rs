use super::get_client;

#[tauri::command]
pub async fn get_item_preferences(item_type: String) -> Result<serde_json::Value, String> {
    get_client().get(&format!("/items/preferences?type={}", item_type)).await
}

#[tauri::command]
pub async fn update_item_preferences(item_type: String, item_id: u64, body: serde_json::Value) -> Result<serde_json::Value, String> {
    get_client().put_json(&format!("/items/{}/{}/preferences", item_type, item_id), &body).await
}
