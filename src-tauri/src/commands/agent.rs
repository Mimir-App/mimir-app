use std::path::PathBuf;
use std::process::Command;

/// Directorio donde se clonan los repos de agentes.
fn agents_dir() -> PathBuf {
    let home = std::env::var("HOME").unwrap_or_default();
    PathBuf::from(home).join(".config").join("mimir").join("agents")
}

/// Intenta inyectar credenciales del keyring en una URL HTTPS de git.
/// Si la URL es de GitHub o del GitLab configurado, usa el token almacenado.
fn inject_credentials(url: &str) -> String {
    // Solo funciona con URLs HTTPS
    if !url.starts_with("https://") {
        return url.to_string();
    }

    // Leer config para obtener gitlab_url
    let config = crate::commands::config::get_config().unwrap_or_default();

    // Detectar si es GitHub
    if url.contains("github.com") {
        if let Ok(Some(token)) = crate::commands::auth::get_credential("github".to_string()) {
            // https://github.com/... → https://oauth2:TOKEN@github.com/...
            return url.replacen("https://github.com", &format!("https://oauth2:{}@github.com", token), 1);
        }
    }

    // Detectar si es el GitLab configurado
    if !config.gitlab_url.is_empty() {
        // Extraer host del gitlab_url (ej: "https://git.example.com" → "git.example.com")
        let gitlab_host = config.gitlab_url
            .trim_end_matches('/')
            .replace("https://", "")
            .replace("http://", "");

        if url.contains(&gitlab_host) {
            if let Ok(Some(token)) = crate::commands::auth::get_credential("gitlab".to_string()) {
                let from = format!("https://{}", gitlab_host);
                let to = format!("https://oauth2:{}@{}", token, gitlab_host);
                return url.replacen(&from, &to, 1);
            }
        }
    }

    url.to_string()
}

/// Comprueba si Claude Code CLI está instalado y autenticado.
/// Usa `claude auth status` para verificar la sesión.
#[tauri::command]
pub fn check_claude_cli() -> Result<serde_json::Value, String> {
    // 1. Verificar que claude está instalado
    let version_output = Command::new("claude")
        .args(["--version"])
        .output();

    let installed = match version_output {
        Ok(output) => output.status.success(),
        Err(_) => false,
    };

    if !installed {
        return Ok(serde_json::json!({
            "installed": false,
            "authenticated": false,
            "version": null,
            "account": null,
        }));
    }

    // Obtener versión
    let version = Command::new("claude")
        .args(["--version"])
        .output()
        .ok()
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .map(|s| s.trim().to_string());

    // 2. Verificar autenticación con `claude auth status`
    let auth_output = Command::new("claude")
        .args(["auth", "status"])
        .output();

    let (authenticated, account) = match auth_output {
        Ok(output) => {
            let stdout = String::from_utf8_lossy(&output.stdout).to_string();
            let stderr = String::from_utf8_lossy(&output.stderr).to_string();
            let combined = format!("{}{}", stdout, stderr);

            // Si el comando tiene éxito y no dice "not logged in" o similar
            let is_auth = output.status.success()
                && !combined.to_lowercase().contains("not logged in")
                && !combined.to_lowercase().contains("not authenticated")
                && !combined.to_lowercase().contains("no active");

            // Intentar extraer cuenta/email del output
            let acc = if is_auth {
                // Buscar patrones como "Logged in as xxx" o email
                combined.lines()
                    .find(|l| l.contains("@") || l.to_lowercase().contains("logged in"))
                    .map(|l| l.trim().to_string())
            } else {
                None
            };

            (is_auth, acc)
        }
        Err(_) => (false, None),
    };

    Ok(serde_json::json!({
        "installed": true,
        "authenticated": authenticated,
        "version": version,
        "account": account,
    }))
}

/// Clona un repositorio de agentes en ~/.config/mimir/agents/.
#[tauri::command]
pub fn clone_agents_repo(url: String) -> Result<serde_json::Value, String> {
    let dir = agents_dir();

    // Si ya existe, eliminar para clonar limpio
    if dir.exists() {
        std::fs::remove_dir_all(&dir)
            .map_err(|e| format!("Error eliminando directorio existente: {}", e))?;
    }

    // Crear directorio padre si no existe
    if let Some(parent) = dir.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| format!("Error creando directorio: {}", e))?;
    }

    // Inyectar credenciales del keyring si la URL es HTTPS y tenemos token
    let clone_url = inject_credentials(&url);

    let output = Command::new("git")
        .args(["clone", &clone_url, &dir.to_string_lossy()])
        .output()
        .map_err(|e| format!("Error ejecutando git clone: {}", e))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Error clonando repositorio: {}", stderr));
    }

    // Contar archivos .md en el repo para informar al usuario
    let agent_count = count_agents(&dir);

    Ok(serde_json::json!({
        "success": true,
        "path": dir.to_string_lossy(),
        "agent_count": agent_count,
    }))
}

/// Actualiza el repositorio de agentes (git pull).
#[tauri::command]
pub fn update_agents_repo() -> Result<serde_json::Value, String> {
    let dir = agents_dir();

    if !dir.exists() || !dir.join(".git").exists() {
        return Err("No hay repositorio de agentes clonado".to_string());
    }

    let output = Command::new("git")
        .args(["pull", "--ff-only"])
        .current_dir(&dir)
        .output()
        .map_err(|e| format!("Error ejecutando git pull: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Error actualizando repositorio: {}", stderr));
    }

    let updated = !stdout.contains("Already up to date");

    Ok(serde_json::json!({
        "success": true,
        "updated": updated,
        "message": stdout.trim(),
    }))
}

/// Genera agentes personalizados usando Claude Code CLI.
/// El prompt del usuario se envía a Claude para que genere la configuración.
#[tauri::command]
pub fn generate_custom_agents(prompt: String) -> Result<serde_json::Value, String> {
    let dir = agents_dir();

    // Crear directorio si no existe
    std::fs::create_dir_all(&dir)
        .map_err(|e| format!("Error creando directorio: {}", e))?;

    let system = format!(
        "Eres un experto en configurar agentes de Claude Code para imputación de horas. \
         El usuario quiere personalizar cómo se generan sus bloques de imputación. \
         Genera los archivos necesarios (CLAUDE.md, .claude/agents/timesheet-generator.md, etc.) \
         en el directorio actual. Responde SOLO con los archivos a crear."
    );

    let output = Command::new("claude")
        .args([
            "--print",
            "--system-prompt", &system,
            "-p", &prompt,
        ])
        .current_dir(&dir)
        .output()
        .map_err(|e| format!("Error ejecutando claude: {}", e))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Error generando agentes: {}", stderr));
    }

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();

    Ok(serde_json::json!({
        "success": true,
        "output": stdout,
        "path": dir.to_string_lossy(),
    }))
}

/// Obtiene info del repositorio de agentes si existe.
#[tauri::command]
pub fn get_agents_repo_info() -> Result<serde_json::Value, String> {
    let dir = agents_dir();

    if !dir.exists() || !dir.join(".git").exists() {
        return Ok(serde_json::json!({
            "exists": false,
        }));
    }

    // Obtener URL remota
    let remote_url = Command::new("git")
        .args(["remote", "get-url", "origin"])
        .current_dir(&dir)
        .output()
        .ok()
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .map(|s| s.trim().to_string());

    // Obtener último commit
    let last_commit = Command::new("git")
        .args(["log", "-1", "--format=%h %s (%cr)"])
        .current_dir(&dir)
        .output()
        .ok()
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .map(|s| s.trim().to_string());

    let agent_count = count_agents(&dir);

    // Verificar si tiene CLAUDE.md o .claude/
    let has_claude_md = dir.join("CLAUDE.md").exists();
    let has_claude_dir = dir.join(".claude").exists();

    Ok(serde_json::json!({
        "exists": true,
        "path": dir.to_string_lossy(),
        "remote_url": remote_url,
        "last_commit": last_commit,
        "agent_count": agent_count,
        "has_claude_md": has_claude_md,
        "has_claude_dir": has_claude_dir,
    }))
}

/// Cuenta archivos .md relevantes (agentes) en el directorio.
fn count_agents(dir: &PathBuf) -> usize {
    let mut count = 0;
    // Contar en .claude/agents/
    let agents_dir = dir.join(".claude").join("agents");
    if agents_dir.exists() {
        if let Ok(entries) = std::fs::read_dir(&agents_dir) {
            count += entries
                .filter_map(|e| e.ok())
                .filter(|e| e.path().extension().map_or(false, |ext| ext == "md"))
                .count();
        }
    }
    // Contar CLAUDE.md en raíz
    if dir.join("CLAUDE.md").exists() {
        count += 1;
    }
    count
}
