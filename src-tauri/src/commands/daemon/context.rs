use super::get_client;

#[tauri::command]
pub async fn get_context_mappings() -> Result<serde_json::Value, String> {
    get_client().get("/context-mappings").await
}

#[tauri::command]
pub async fn suggest_context_mapping(context_key: String) -> Result<serde_json::Value, String> {
    get_client()
        .get(&format!("/context-mappings/suggest?context_key={}", urlencoding::encode(&context_key)))
        .await
}

#[tauri::command]
pub async fn save_context_mapping(mapping: serde_json::Value) -> Result<serde_json::Value, String> {
    get_client().put_json("/context-mappings", &mapping).await
}

#[tauri::command]
pub async fn delete_context_mapping(context_key: String) -> Result<(), String> {
    get_client()
        .delete(&format!("/context-mappings/{}", urlencoding::encode(&context_key)))
        .await
}
