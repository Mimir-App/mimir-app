use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimesheetEntry {
    pub id: i64,
    pub date: String,
    pub project_id: i64,
    pub project_name: String,
    pub task_id: Option<i64>,
    pub task_name: Option<String>,
    pub description: String,
    pub hours: f64,
    pub employee_id: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OdooProject {
    pub id: i64,
    pub name: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OdooTask {
    pub id: i64,
    pub name: String,
    pub project_id: i64,
}
