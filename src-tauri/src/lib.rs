mod clients;
mod commands;
mod models;

use commands::{auth, config, daemon};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            // Daemon proxy
            daemon::get_daemon_status,
            daemon::daemon_health_check,
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
            // Config
            config::get_config,
            config::save_config,
            // Auth
            auth::store_credential,
            auth::get_credential,
            auth::delete_credential,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
