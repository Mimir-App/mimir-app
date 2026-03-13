/// Gestión de credenciales usando el keyring del sistema.
///
/// Almacena tokens de GitLab y Odoo de forma segura.

#[tauri::command]
pub fn store_credential(service: String, token: String) -> Result<(), String> {
    let entry = keyring::Entry::new("mimir", &service)
        .map_err(|e| format!("Error accediendo al keyring: {}", e))?;
    entry
        .set_password(&token)
        .map_err(|e| format!("Error guardando credencial: {}", e))
}

#[tauri::command]
pub fn get_credential(service: String) -> Result<Option<String>, String> {
    let entry = keyring::Entry::new("mimir", &service)
        .map_err(|e| format!("Error accediendo al keyring: {}", e))?;
    match entry.get_password() {
        Ok(password) => Ok(Some(password)),
        Err(keyring::Error::NoEntry) => Ok(None),
        Err(e) => Err(format!("Error leyendo credencial: {}", e)),
    }
}

#[tauri::command]
pub fn delete_credential(service: String) -> Result<(), String> {
    let entry = keyring::Entry::new("mimir", &service)
        .map_err(|e| format!("Error accediendo al keyring: {}", e))?;
    match entry.delete_credential() {
        Ok(()) => Ok(()),
        Err(keyring::Error::NoEntry) => Ok(()),
        Err(e) => Err(format!("Error eliminando credencial: {}", e)),
    }
}
