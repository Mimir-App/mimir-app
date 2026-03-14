use std::process::{Child, Command};
use std::sync::Mutex;

static SERVER_PROCESS: Mutex<Option<Child>> = Mutex::new(None);

/// Intenta encontrar el binario mimir-server en varias ubicaciones.
fn find_server_binary() -> Option<String> {
    let home = std::env::var("HOME").unwrap_or_default();
    let candidates = [
        // Binario instalado en ~/.local/bin
        format!("{}/.local/bin/mimir-server", home),
        // Binario en dist/daemon/ (desarrollo)
        "dist/daemon/mimir-server".to_string(),
    ];

    for path in &candidates {
        if std::path::Path::new(path).exists() {
            return Some(path.clone());
        }
    }

    // Relativo al ejecutable actual
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
        return; // Ya está corriendo
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
        // Fallback: intentar con python
        match Command::new("python3")
            .args(["-m", "mimir_daemon.api_server"])
            .spawn()
        {
            Ok(child) => {
                eprintln!("[mimir] mimir-server arrancado via python3 (pid: {})", child.id());
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
