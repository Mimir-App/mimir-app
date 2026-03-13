use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GitLabUser {
    pub id: i64,
    pub username: String,
    pub name: String,
    pub avatar_url: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GitLabIssue {
    pub id: i64,
    pub iid: i64,
    pub title: String,
    pub description: Option<String>,
    pub state: String,
    pub web_url: String,
    pub project_path: String,
    pub labels: Vec<String>,
    pub assignees: Vec<GitLabUser>,
    pub milestone: Option<String>,
    pub due_date: Option<String>,
    pub created_at: String,
    pub updated_at: String,
    pub user_notes_count: u32,
    pub has_conflicts: bool,
    pub score: f64,
    pub manual_priority: Option<f64>,
}
