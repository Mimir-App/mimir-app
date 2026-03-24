use crate::models::block::{ActivityBlock, BlockUpdate};

use super::get_client;

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
