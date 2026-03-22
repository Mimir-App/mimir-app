use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PriorityLabelMapping {
    pub label: String,
    pub weight: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct AppConfig {
    pub daemon_port: u16,
    pub gitlab_url: String,
    pub gitlab_token_stored: bool,
    pub github_token_stored: bool,
    pub odoo_url: String,
    pub odoo_version: String,
    pub odoo_db: String,
    pub odoo_username: String,
    pub odoo_token_stored: bool,
    pub theme: String,
    pub refresh_interval_seconds: u32,
    pub daily_hour_target: f64,
    pub weekly_hour_targets: Vec<f64>,
    pub ai_provider: String,
    pub ai_api_key_stored: bool,
    pub ai_user_role: String,
    pub ai_custom_context: String,
    pub hour_format: String,
    pub date_format: String,
    pub font_size: u32,
    pub dashboard_order: Vec<String>,
    pub dashboard_spans: std::collections::HashMap<String, Vec<u32>>,
    pub column_widths: std::collections::HashMap<String, u32>,
    pub timezone: String,
    pub signals_retention_days: u32,
    pub blocks_retention_days: u32,
    pub google_client_id: String,
    pub google_client_secret: String,
    pub capture_window: bool,
    pub capture_git: bool,
    pub capture_idle: bool,
    pub capture_audio: bool,
    pub capture_ssh: bool,
    pub inactivity_threshold_minutes: u32,
    pub gitlab_priority_labels: Vec<PriorityLabelMapping>,
    pub issue_notes_count: u32,
    pub dashboard_widgets: Vec<serde_json::Value>,
    pub notification_enabled: bool,
    pub notification_interval_minutes: u32,
    pub notification_retention_days: u32,
    pub notification_comments: bool,
    pub notification_pipeline_failed: bool,
    pub notification_mr_approved: bool,
    pub notification_changes_requested: bool,
    pub notification_conflicts: bool,
    pub notification_todos: bool,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            daemon_port: 9477,
            gitlab_url: String::new(),
            gitlab_token_stored: false,
            github_token_stored: false,
            odoo_url: String::new(),
            odoo_version: "v16".to_string(),
            odoo_db: String::new(),
            odoo_username: String::new(),
            odoo_token_stored: false,
            theme: "dark".to_string(),
            refresh_interval_seconds: 300,
            daily_hour_target: 8.0,
            weekly_hour_targets: vec![8.0, 8.0, 8.0, 8.0, 8.0, 0.0, 0.0],
            ai_provider: "none".to_string(),
            ai_api_key_stored: false,
            ai_user_role: "technical".to_string(),
            ai_custom_context: String::new(),
            hour_format: "hm".to_string(),
            date_format: "eu".to_string(),
            font_size: 14,
            dashboard_order: vec![],
            dashboard_spans: std::collections::HashMap::<String, Vec<u32>>::new(),
            column_widths: std::collections::HashMap::new(),
            timezone: "Europe/Madrid".to_string(),
            signals_retention_days: 90,
            blocks_retention_days: 180,
            google_client_id: String::new(),
            google_client_secret: String::new(),
            capture_window: true,
            capture_git: true,
            capture_idle: true,
            capture_audio: true,
            capture_ssh: true,
            inactivity_threshold_minutes: 5,
            gitlab_priority_labels: vec![
                PriorityLabelMapping { label: "priority::critical".to_string(), weight: 100 },
                PriorityLabelMapping { label: "priority::high".to_string(), weight: 75 },
                PriorityLabelMapping { label: "priority::medium".to_string(), weight: 50 },
                PriorityLabelMapping { label: "priority::low".to_string(), weight: 25 },
                PriorityLabelMapping { label: "Expedite".to_string(), weight: 100 },
            ],
            issue_notes_count: 5,
            dashboard_widgets: vec![],
            notification_enabled: true,
            notification_interval_minutes: 5,
            notification_retention_days: 7,
            notification_comments: true,
            notification_pipeline_failed: true,
            notification_mr_approved: true,
            notification_changes_requested: true,
            notification_conflicts: true,
            notification_todos: true,
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
