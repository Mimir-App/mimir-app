use serde::{Deserialize, Serialize};
use super::issue::GitLabUser;

#[allow(dead_code)]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GitLabMergeRequest {
    #[serde(default)]
    pub id: i64,
    #[serde(default)]
    pub iid: i64,
    #[serde(default)]
    pub title: String,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub state: String,
    #[serde(default)]
    pub web_url: String,
    #[serde(default)]
    pub project_path: String,
    #[serde(default)]
    pub labels: Vec<String>,
    #[serde(default)]
    pub assignees: Vec<GitLabUser>,
    #[serde(default)]
    pub reviewers: Vec<GitLabUser>,
    #[serde(default)]
    pub source_branch: String,
    #[serde(default)]
    pub target_branch: String,
    #[serde(default)]
    pub has_conflicts: bool,
    #[serde(default)]
    pub pipeline_status: Option<String>,
    #[serde(default)]
    pub created_at: String,
    #[serde(default)]
    pub updated_at: String,
    #[serde(default)]
    pub user_notes_count: u32,
    #[serde(default)]
    pub score: f64,
    #[serde(default)]
    pub manual_priority: Option<f64>,
}
