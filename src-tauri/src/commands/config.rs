use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub daemon_port: u16,
    pub gitlab_url: String,
    pub gitlab_token_stored: bool,
    pub odoo_url: String,
    pub odoo_version: String,
    pub odoo_db: String,
    pub odoo_username: String,
    pub odoo_token_stored: bool,
    pub theme: String,
    pub refresh_interval_seconds: u32,
    pub daily_hour_target: f64,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            daemon_port: 9477,
            gitlab_url: String::new(),
            gitlab_token_stored: false,
            odoo_url: String::new(),
            odoo_version: "v16".to_string(),
            odoo_db: String::new(),
            odoo_username: String::new(),
            odoo_token_stored: false,
            theme: "dark".to_string(),
            refresh_interval_seconds: 300,
            daily_hour_target: 8.0,
        }
    }
}

fn config_path() -> PathBuf {
    let home = dirs::config_dir().unwrap_or_else(|| PathBuf::from("."));
    home.join("mimir").join("config.json")
}

#[tauri::command]
pub fn get_config() -> Result<AppConfig, String> {
    let path = config_path();
    if !path.exists() {
        return Ok(AppConfig::default());
    }
    let content = fs::read_to_string(&path).map_err(|e| format!("Error leyendo config: {}", e))?;
    serde_json::from_str(&content).map_err(|e| format!("Error parseando config: {}", e))
}

#[tauri::command]
pub fn save_config(config: AppConfig) -> Result<(), String> {
    let path = config_path();
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| format!("Error creando directorio: {}", e))?;
    }
    let json =
        serde_json::to_string_pretty(&config).map_err(|e| format!("Error serializando: {}", e))?;
    fs::write(&path, json).map_err(|e| format!("Error escribiendo config: {}", e))
}
