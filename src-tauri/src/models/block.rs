use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActivityBlock {
    pub id: i64,
    pub start_time: String,
    pub end_time: String,
    pub duration_minutes: f64,
    pub app_name: String,
    pub window_title: String,
    pub project_path: Option<String>,
    pub git_branch: Option<String>,
    pub git_remote: Option<String>,
    pub ai_description: Option<String>,
    pub ai_confidence: Option<f64>,
    pub user_description: Option<String>,
    pub odoo_project_id: Option<i64>,
    pub odoo_task_id: Option<i64>,
    pub odoo_project_name: Option<String>,
    pub odoo_task_name: Option<String>,
    pub status: String,
    pub sync_error: Option<String>,
    pub odoo_entry_id: Option<i64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BlockUpdate {
    pub user_description: Option<String>,
    pub odoo_project_id: Option<i64>,
    pub odoo_task_id: Option<i64>,
    pub odoo_project_name: Option<String>,
    pub odoo_task_name: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DaemonStatus {
    pub running: bool,
    pub mode: String,
    pub uptime_seconds: u64,
    pub last_poll: Option<String>,
    pub blocks_today: u32,
    pub version: String,
}
