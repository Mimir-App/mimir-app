use std::process::{Child, Command};
use std::sync::Mutex;

static SERVER_PROCESS: Mutex<Option<Child>> = Mutex::new(None);

/// Intenta encontrar el binario mimir-server en varias ubicaciones.
fn find_server_binary() -> Option<String> {
    let home = std::env::var("HOME").unwrap_or_default();
    let candidates = [
        "/usr/bin/mimir-server".to_string(),
        format!("{}/.local/bin/mimir-server", home),
        "dist/daemon/mimir-server".to_string(),
    ];

    for path in &candidates {
        if std::path::Path::new(path).exists() {
            return Some(path.clone());
        }
    }

    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            let candidate = dir.join("mimir-server");
            if candidate.exists() {
                return Some(candidate.to_string_lossy().to_string());
            }
        }
    }

    None
}

/// Arranca mimir-server como proceso hijo.
pub fn start_server() {
    let mut guard = SERVER_PROCESS.lock().unwrap();
    if guard.is_some() {
        return;
    }

    if let Some(binary) = find_server_binary() {
        match Command::new(&binary).spawn() {
            Ok(child) => {
                eprintln!("[mimir] mimir-server arrancado (pid: {}, binary: {})", child.id(), binary);
                *guard = Some(child);
            }
            Err(e) => {
                eprintln!("[mimir] Error arrancando mimir-server ({}): {}", binary, e);
            }
        }
    } else {
        // En desarrollo, intentar usar el venv del daemon si existe
        let venv_python_candidates = [
            "daemon/.venv/bin/python".to_string(),
            format!("{}/daemon/.venv/bin/python",
                std::env::current_dir().unwrap_or_default().display()),
            "/opt/Mimir/mimir-app/daemon/.venv/bin/python".to_string(),
        ];
        let python = venv_python_candidates.iter()
            .find(|p| std::path::Path::new(p).exists())
            .cloned()
            .unwrap_or_else(|| "python3".to_string());

        match Command::new(&python)
            .args(["-m", "mimir_daemon.api_server"])
            .spawn()
        {
            Ok(child) => {
                eprintln!("[mimir] mimir-server arrancado via {} (pid: {})", python, child.id());
                *guard = Some(child);
            }
            Err(e) => {
                eprintln!("[mimir] No se pudo arrancar mimir-server: {}", e);
            }
        }
    }
}

/// Mata el proceso mimir-server.
pub fn stop_server() {
    let mut guard = SERVER_PROCESS.lock().unwrap();
    if let Some(mut child) = guard.take() {
        eprintln!("[mimir] Deteniendo mimir-server (pid: {})", child.id());
        let _ = child.kill();
        let _ = child.wait();
    }
}

/// Controla mimir-capture via systemctl --user.
fn systemctl_capture(action: &str) -> Result<String, String> {
    let output = Command::new("systemctl")
        .args(["--user", action, "mimir-capture"])
        .output()
        .map_err(|e| format!("Error ejecutando systemctl: {}", e))?;

    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        Err(format!("systemctl {} fallo: {}", action, stderr))
    }
}

// --- Tauri commands ---

#[tauri::command]
pub fn start_capture_service() -> Result<String, String> {
    systemctl_capture("start")
}

#[tauri::command]
pub fn stop_capture_service() -> Result<String, String> {
    systemctl_capture("stop")
}

#[tauri::command]
pub fn restart_capture_service() -> Result<String, String> {
    systemctl_capture("restart")
}

#[tauri::command]
pub fn start_server_service() -> Result<(), String> {
    start_server();
    Ok(())
}

#[tauri::command]
pub fn stop_server_service() -> Result<(), String> {
    stop_server();
    Ok(())
}

#[tauri::command]
pub fn restart_server_service() -> Result<(), String> {
    stop_server();
    start_server();
    Ok(())
}
