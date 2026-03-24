use super::get_client;

#[tauri::command]
pub async fn get_issues() -> Result<Vec<serde_json::Value>, String> {
    get_client().get("/gitlab/issues").await
}

#[tauri::command]
pub async fn get_merge_requests() -> Result<Vec<serde_json::Value>, String> {
    get_client().get("/gitlab/merge_requests").await
}

// --- GitLab Issues (search, followed, labels, notes) ---

#[tauri::command]
pub async fn search_gitlab_issues(q: String) -> Result<serde_json::Value, String> {
    get_client().get(&format!("/gitlab/issues/search?q={}", q)).await
}

#[tauri::command]
pub async fn get_followed_issues() -> Result<serde_json::Value, String> {
    get_client().get("/gitlab/issues/followed").await
}

#[tauri::command]
pub async fn get_gitlab_labels() -> Result<serde_json::Value, String> {
    get_client().get("/gitlab/labels").await
}

#[tauri::command]
pub async fn get_issue_notes(project_id: String, issue_iid: u64, per_page: u32) -> Result<serde_json::Value, String> {
    get_client().get(&format!("/gitlab/issues/{}/{}/notes?per_page={}", project_id, issue_iid, per_page)).await
}

// --- GitLab Merge Requests (search, followed, notes, conflicts) ---

#[tauri::command]
pub async fn search_gitlab_merge_requests(q: String) -> Result<serde_json::Value, String> {
    get_client().get(&format!("/gitlab/merge_requests/search?q={}", q)).await
}

#[tauri::command]
pub async fn get_followed_merge_requests() -> Result<serde_json::Value, String> {
    get_client().get("/gitlab/merge_requests/followed").await
}

#[tauri::command]
pub async fn get_mr_notes(project_id: String, mr_iid: u64, per_page: u32) -> Result<serde_json::Value, String> {
    get_client().get(&format!("/gitlab/merge_requests/{}/{}/notes?per_page={}", project_id, mr_iid, per_page)).await
}

#[tauri::command]
pub async fn get_mr_conflicts(project_id: String, mr_iid: u64) -> Result<serde_json::Value, String> {
    get_client().get(&format!("/gitlab/merge_requests/{}/{}/conflicts", project_id, mr_iid)).await
}

// --- GitHub ---

#[tauri::command]
pub async fn get_github_issue_comments(owner: String, repo: String, issue_number: u64, per_page: u32) -> Result<Vec<serde_json::Value>, String> {
    get_client().get(&format!("/github/issues/{}/{}/{}/comments?per_page={}", owner, repo, issue_number, per_page)).await
}

#[tauri::command]
pub async fn search_github_issues(q: String) -> Result<Vec<serde_json::Value>, String> {
    get_client().get(&format!("/github/issues/search?q={}", urlencoding::encode(&q))).await
}

#[tauri::command]
pub async fn search_github_pull_requests(q: String) -> Result<Vec<serde_json::Value>, String> {
    get_client().get(&format!("/github/pull_requests/search?q={}", urlencoding::encode(&q))).await
}

// --- GitLab Todos & User ---

#[tauri::command]
pub async fn get_gitlab_todos() -> Result<serde_json::Value, String> {
    get_client().get("/gitlab/todos").await
}

#[tauri::command]
pub async fn get_gitlab_user() -> Result<serde_json::Value, String> {
    get_client().get("/gitlab/user").await
}
