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

// --- Helpers de agentes ---

/// Busca un agente .md por nombre en rutas conocidas (built-in).
/// Retorna la ruta del primer archivo encontrado.
fn find_agent(name: &str) -> Option<String> {
    let home = std::env::var("HOME").unwrap_or_default();
    [
        format!("/usr/share/mimir/agents/{}.md", name),
        format!("{}/.local/share/mimir/agents/{}.md", home, name),
        std::env::current_dir()
            .unwrap_or_default()
            .join(format!(".claude/agents/{}.md", name))
            .to_string_lossy()
            .to_string(),
        format!("/opt/Mimir/mimir-app/.claude/agents/{}.md", name),
    ]
    .into_iter()
    .find(|p| std::path::Path::new(p).exists())
}

/// Busca reglas opcionales para un agente (ej: timesheet-rules.md).
fn find_rules(name: &str) -> Option<String> {
    let home = std::env::var("HOME").unwrap_or_default();
    [
        format!("{}/.config/mimir/{}.md", home, name),
        format!("/usr/share/mimir/agents/{}.md", name),
    ]
    .iter()
    .find(|p| std::path::Path::new(p).exists())
    .and_then(|p| std::fs::read_to_string(p).ok())
}

/// Obtiene el directorio del repo de agentes si está habilitado y existe.
fn get_repo_dir() -> Option<String> {
    let home = std::env::var("HOME").unwrap_or_default();
    let agents_repo_dir = format!("{}/.config/mimir/agents", home);
    let agents_repo_exists = std::path::Path::new(&agents_repo_dir)
        .join(".git")
        .exists();
    let config = crate::commands::config::get_config().unwrap_or_default();
    if config.agents_repo_enabled && agents_repo_exists {
        Some(agents_repo_dir)
    } else {
        None
    }
}

/// Construye el system prompt completo para un agente.
///
/// Prioridad:
/// 1. Si hay repo con su propia versión del agente → usa la del repo
/// 2. Si no → usa el built-in
///
/// Siempre anexa:
/// - Reglas del usuario (timesheet-rules.md) si existen
/// - CLAUDE.md del repo si existe (como contexto extra)
fn build_full_prompt(agent_name: &str, rules_name: &str, repo_dir: Option<&str>) -> Result<String, String> {
    // 1. Contenido del agente: repo o built-in
    let agent_content = if let Some(dir) = repo_dir {
        let repo_agent = std::path::Path::new(dir)
            .join(".claude")
            .join("agents")
            .join(format!("{}.md", agent_name));
        if repo_agent.exists() {
            eprintln!("[mimir] Usando agente del repo: {}", repo_agent.display());
            std::fs::read_to_string(&repo_agent)
                .map_err(|e| format!("Error leyendo agente del repo: {}", e))?
        } else {
            eprintln!("[mimir] Repo no tiene {}.md, usando built-in", agent_name);
            let path = find_agent(agent_name)
                .ok_or_else(|| format!("No se encontró {}.md", agent_name))?;
            std::fs::read_to_string(&path)
                .map_err(|e| format!("Error leyendo agente: {}", e))?
        }
    } else {
        let path = find_agent(agent_name)
            .ok_or_else(|| format!("No se encontró {}.md", agent_name))?;
        std::fs::read_to_string(&path)
            .map_err(|e| format!("Error leyendo agente: {}", e))?
    };

    let mut prompt = agent_content;

    // 2. Reglas del usuario
    if let Some(rules) = find_rules(rules_name) {
        prompt.push_str("\n\n## Reglas de matching del usuario\n\n");
        prompt.push_str(&rules);
    }

    // 3. CLAUDE.md del repo como contexto extra
    if let Some(dir) = repo_dir {
        let claude_md = std::path::Path::new(dir).join("CLAUDE.md");
        if claude_md.exists() {
            if let Ok(content) = std::fs::read_to_string(&claude_md) {
                prompt.push_str("\n\n## Contexto del repositorio de agentes\n\n");
                prompt.push_str(&content);
            }
        }
    }

    Ok(prompt)
}

/// Invoca Claude CLI con system prompt + prompt, opcionalmente con cwd=repo.
fn invoke_claude(
    prompt: &str,
    system_prompt: &str,
    repo_dir: Option<&str>,
    debug_file: &str,
) -> Result<std::process::Output, String> {
    // Asegurar que el archivo MCP vacío existe
    let mcp_path = "/tmp/mimir-empty-mcp.json";
    if !std::path::Path::new(mcp_path).exists() {
        let _ = std::fs::write(mcp_path, r#"{"mcpServers":{}}"#);
    }

    let mut cmd = Command::new("claude");
    let args = [
        "--print",
        "--no-session-persistence",
        "--system-prompt", system_prompt,
        "--permission-mode", "plan",
        "--model", "haiku",
        "--disable-slash-commands",
        "--mcp-config", mcp_path,
        "--debug-file", debug_file,
        "-p", prompt,
    ];

    cmd.args(args);

    if let Some(dir) = repo_dir {
        cmd.current_dir(dir);
    }

    cmd.output()
        .map_err(|e| format!("Error ejecutando claude CLI: {}. ¿Está instalado?", e))
}

/// Genera bloques de imputación invocando el agente Claude Code CLI.
///
/// Recopila todos los datos del día via mimir-server, los pasa en el prompt
/// para que Claude no necesite hacer tool calls, y parsea el JSON resultante.
#[tauri::command]
pub async fn generate_blocks_with_agent(
    date: String,
    target_hours: Option<f64>,
) -> Result<serde_json::Value, String> {
    let client = get_client();

    // 1. Recopilar todos los datos via endpoint unificado del server
    let gen_data: serde_json::Value = client
        .get(&format!("/blocks/generation-data?date={}", date))
        .await
        .map_err(|e| format!("Error recopilando datos: {}", e))?;

    let data_context = serde_json::to_string(&gen_data).unwrap_or_default();
    eprintln!("[mimir-agent] Datos recopilados para {}: {} bytes", date, data_context.len());
    eprintln!(
        "[mimir-agent] Data JSON:\n{}",
        serde_json::to_string_pretty(&gen_data).unwrap_or_default()
    );

    let prompt = if let Some(hours) = target_hours {
        format!(
            "Genera bloques para {date} que sumen exactamente {hours:.1} horas de trabajo. \
             NO ejecutes comandos. Devuelve SOLO JSON. Datos:\n\n{data}",
            date = date,
            hours = hours,
            data = data_context
        )
    } else {
        format!(
            "Genera bloques para {date}. NO ejecutes comandos. Devuelve SOLO JSON. Datos:\n\n{data}",
            date = date,
            data = data_context
        )
    };

    let debug_file = format!("/tmp/mimir-claude-debug-{}.log", date);
    let cli_start = std::time::Instant::now();

    // 2. Construir system prompt (built-in o repo) + invocar Claude
    let repo_dir = get_repo_dir();
    let system_prompt = build_full_prompt(
        "timesheet-generator",
        "timesheet-rules",
        repo_dir.as_deref(),
    )?;
    eprintln!(
        "[mimir-agent] System prompt: {} bytes, repo: {}",
        system_prompt.len(),
        repo_dir.as_deref().unwrap_or("ninguno")
    );

    let output = invoke_claude(&prompt, &system_prompt, repo_dir.as_deref(), &debug_file)?;

    let cli_elapsed = cli_start.elapsed();
    eprintln!("[mimir-agent] Claude CLI terminó en {:.1}s", cli_elapsed.as_secs_f64());

    let stderr_str = String::from_utf8_lossy(&output.stderr);
    if !stderr_str.is_empty() {
        eprintln!(
            "[mimir-agent] Claude stderr: {}",
            &stderr_str[..stderr_str.len().min(500)]
        );
    }
    eprintln!("[mimir-agent] Debug log en: {}", debug_file);

    if !output.status.success() {
        return Err(format!(
            "Claude CLI falló (exit {}): {}",
            output.status, stderr_str
        ));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    eprintln!("[mimir-agent] Stdout: {} bytes", stdout.len());

    // 3. Extraer y enviar JSON
    let json_str = extract_json(&stdout).ok_or_else(|| {
        format!(
            "No se encontró JSON válido en la salida: {}",
            &stdout[..stdout.len().min(500)]
        )
    })?;

    let blocks_data: serde_json::Value =
        serde_json::from_str(json_str).map_err(|e| format!("Error parseando JSON: {}", e))?;

    get_client()
        .post::<serde_json::Value, _>("/blocks/generate", &blocks_data)
        .await
}

/// Revisa bloques generados invocando el agente reviewer Claude Code CLI.
///
/// Obtiene los bloques actuales + datos de generación, los pasa al reviewer
/// y retorna el JSON con issues y summary.
#[tauri::command]
pub async fn review_blocks_with_agent(date: String) -> Result<serde_json::Value, String> {
    let client = get_client();

    // 1. Obtener datos de revisión (bloques + generation-data)
    let review_data: serde_json::Value = client
        .get(&format!("/blocks/review-data?date={}", date))
        .await
        .map_err(|e| format!("Error obteniendo datos de revisión: {}", e))?;

    let data_context = serde_json::to_string(&review_data).unwrap_or_default();
    eprintln!(
        "[mimir-reviewer] Datos de revisión para {}: {} bytes",
        date,
        data_context.len()
    );

    let prompt = format!(
        "Revisa los bloques generados para {date}. NO ejecutes comandos. Devuelve SOLO JSON.\n\nDatos:\n\n{data}",
        date = date,
        data = data_context
    );

    let debug_file = format!("/tmp/mimir-reviewer-debug-{}.log", date);
    let cli_start = std::time::Instant::now();

    // 2. Construir system prompt (built-in o repo) + invocar Claude
    let repo_dir = get_repo_dir();
    let system_prompt = build_full_prompt(
        "timesheet-reviewer",
        "timesheet-rules",
        repo_dir.as_deref(),
    )?;
    eprintln!(
        "[mimir-reviewer] System prompt: {} bytes, repo: {}",
        system_prompt.len(),
        repo_dir.as_deref().unwrap_or("ninguno")
    );

    let output = invoke_claude(&prompt, &system_prompt, repo_dir.as_deref(), &debug_file)?;

    let cli_elapsed = cli_start.elapsed();
    eprintln!(
        "[mimir-reviewer] Claude CLI terminó en {:.1}s",
        cli_elapsed.as_secs_f64()
    );

    let stderr_str = String::from_utf8_lossy(&output.stderr);
    if !stderr_str.is_empty() {
        eprintln!(
            "[mimir-reviewer] Claude stderr: {}",
            &stderr_str[..stderr_str.len().min(500)]
        );
    }

    if !output.status.success() {
        return Err(format!(
            "Claude CLI falló (exit {}): {}",
            output.status, stderr_str
        ));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    eprintln!("[mimir-reviewer] Stdout: {} bytes", stdout.len());

    // 3. Extraer JSON (no se envía al daemon — solo se retorna al frontend)
    let json_str = extract_json(&stdout).ok_or_else(|| {
        format!(
            "No se encontró JSON válido en la salida del reviewer: {}",
            &stdout[..stdout.len().min(500)]
        )
    })?;

    serde_json::from_str(json_str).map_err(|e| format!("Error parseando JSON del reviewer: {}", e))
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
