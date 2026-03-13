use serde::{Deserialize, Serialize};
use super::issue::GitLabUser;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GitLabMergeRequest {
    pub id: i64,
    pub iid: i64,
    pub title: String,
    pub description: Option<String>,
    pub state: String,
    pub web_url: String,
    pub project_path: String,
    pub labels: Vec<String>,
    pub assignees: Vec<GitLabUser>,
    pub reviewers: Vec<GitLabUser>,
    pub source_branch: String,
    pub target_branch: String,
    pub has_conflicts: bool,
    pub pipeline_status: Option<String>,
    pub created_at: String,
    pub updated_at: String,
    pub user_notes_count: u32,
    pub score: f64,
    pub manual_priority: Option<f64>,
}
