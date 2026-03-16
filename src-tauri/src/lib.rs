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
