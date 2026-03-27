use std::process::Command;

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

/// Genera bloques de imputación invocando el agente Claude Code CLI.
///
/// Recopila todos los datos del día via mimir-server, los pasa en el prompt
/// para que Claude no necesite hacer tool calls, y parsea el JSON resultante.
#[tauri::command]
pub async fn generate_blocks_with_agent(date: String) -> Result<serde_json::Value, String> {
    let client = get_client();

    // 1. Recopilar todos los datos via endpoint unificado del server
    let data_url = format!("/blocks/generation-data?date={}", date);
    let gen_data: serde_json::Value = client.get(&data_url).await
        .map_err(|e| format!("Error recopilando datos: {}", e))?;

    let data_context = serde_json::to_string_pretty(&gen_data).unwrap_or_default();

    // 2. Buscar agente y reglas de matching
    let home = std::env::var("HOME").unwrap_or_default();
    let agent_paths = [
        "/usr/share/mimir/agents/timesheet-generator.md".to_string(),
        format!("{}/.local/share/mimir/agents/timesheet-generator.md", home),
        std::env::current_dir()
            .unwrap_or_default()
            .join(".claude/agents/timesheet-generator.md")
            .to_string_lossy()
            .to_string(),
        "/opt/Mimir/mimir-app/.claude/agents/timesheet-generator.md".to_string(),
    ];
    let agent_path = agent_paths.into_iter()
        .find(|p| std::path::Path::new(p).exists())
        .ok_or_else(|| "No se encontró timesheet-generator.md".to_string())?;

    let agent_content = std::fs::read_to_string(&agent_path)
        .map_err(|e| format!("Error leyendo agente: {}", e))?;

    // Leer reglas de matching (opcional)
    let rules_paths = [
        format!("{}/.config/mimir/timesheet-rules.md", home),
        "/usr/share/mimir/agents/timesheet-rules.md".to_string(),
    ];
    let rules = rules_paths.iter()
        .find(|p| std::path::Path::new(p).exists())
        .and_then(|p| std::fs::read_to_string(p).ok())
        .unwrap_or_default();

    let system_prompt = if rules.is_empty() {
        agent_content
    } else {
        format!("{}\n\n## Reglas de matching del usuario\n\n{}", agent_content, rules)
    };

    let prompt = format!(
        "Genera bloques para {date}. NO ejecutes comandos. Datos:\n\n{data}",
        date = date,
        data = data_context
    );

    // 3. Ejecutar claude CLI (sin tool calls, solo razonamiento)
    let output = Command::new("claude")
        .args([
            "--print",
            "--system-prompt", &system_prompt,
            "--permission-mode", "plan",
            "--model", "haiku",
            "-p", &prompt,
        ])
        .output()
        .map_err(|e| format!("Error ejecutando claude CLI: {}. ¿Está instalado?", e))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Claude CLI falló: {}", stderr));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);

    // 4. Extraer y enviar JSON
    let json_str = extract_json(&stdout)
        .ok_or_else(|| format!("No se encontró JSON válido en la salida: {}", &stdout[..stdout.len().min(500)]))?;

    let blocks_data: serde_json::Value = serde_json::from_str(json_str)
        .map_err(|e| format!("Error parseando JSON: {}", e))?;

    get_client()
        .post::<serde_json::Value, _>("/blocks/generate", &blocks_data)
        .await
}

/// Extrae el primer objeto JSON `{...}` completo de un string.
fn extract_json(text: &str) -> Option<&str> {
    let start = text.find('{')?;
    let mut depth = 0;
    let mut in_string = false;
    let mut escape = false;

    for (i, ch) in text[start..].char_indices() {
        if escape {
            escape = false;
            continue;
        }
        match ch {
            '\\' if in_string => escape = true,
            '"' => in_string = !in_string,
            '{' if !in_string => depth += 1,
            '}' if !in_string => {
                depth -= 1;
                if depth == 0 {
                    return Some(&text[start..start + i + 1]);
                }
            }
            _ => {}
        }
    }
    None
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
