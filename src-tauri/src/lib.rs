mod clients;
mod commands;
mod models;
mod server_process;

use commands::{auth, config, daemon};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Arranca mimir-server al iniciar la app
    server_process::start_server();

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                if window.label() == "main" {
                    server_process::stop_server();
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            // Daemon proxy
            daemon::get_daemon_status,
            daemon::daemon_health_check,
            daemon::capture_health_check,
            daemon::get_capture_health,
            daemon::set_daemon_mode,
            daemon::get_blocks,
            daemon::confirm_block,
            daemon::update_block,
            daemon::delete_block,
            daemon::sync_blocks_to_odoo,
            daemon::retry_sync_block,
            daemon::get_odoo_projects,
            daemon::get_odoo_tasks,
            daemon::get_timesheet_entries,
            daemon::get_issues,
            daemon::get_merge_requests,
            daemon::push_config_to_daemon,
            daemon::generate_block_description,
            daemon::get_integration_status,
            daemon::get_signals,
            daemon::split_block,
            daemon::merge_blocks,
            daemon::get_google_auth_url,
            daemon::get_google_calendar_status,
            daemon::disconnect_google_calendar,
            daemon::get_attendance_today,
            daemon::attendance_check_in,
            daemon::attendance_check_out,
            // Item preferences (generic)
            daemon::get_item_preferences,
            daemon::update_item_preferences,
            // GitLab issues extended
            daemon::search_gitlab_issues,
            daemon::get_followed_issues,
            daemon::get_gitlab_labels,
            daemon::get_issue_notes,
            // GitLab merge requests extended
            daemon::search_gitlab_merge_requests,
            daemon::get_followed_merge_requests,
            daemon::get_mr_notes,
            daemon::get_mr_conflicts,
            // GitHub
            daemon::get_github_issue_comments,
            daemon::search_github_issues,
            daemon::search_github_pull_requests,
            // GitLab todos & user
            daemon::get_gitlab_todos,
            daemon::get_gitlab_user,
            // GitHub OAuth
            daemon::github_oauth_start,
            daemon::github_oauth_poll,
            // Notifications
            daemon::get_notifications,
            daemon::get_notification_count,
            daemon::mark_notification_read,
            daemon::mark_all_notifications_read,
            // Context mappings
            daemon::get_context_mappings,
            daemon::suggest_context_mapping,
            daemon::save_context_mapping,
            daemon::delete_context_mapping,
            // Odoo entries
            daemon::update_timesheet_entry,
            // Config
            config::get_config,
            config::save_config,
            // Auth
            auth::store_credential,
            auth::get_credential,
            auth::delete_credential,
            // Service control
            server_process::start_capture_service,
            server_process::stop_capture_service,
            server_process::restart_capture_service,
            server_process::start_server_service,
            server_process::stop_server_service,
            server_process::restart_server_service,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
