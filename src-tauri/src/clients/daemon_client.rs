use serde::de::DeserializeOwned;

/// Cliente HTTP para comunicarse con el daemon Python local.
pub struct DaemonClient {
    base_url: String,
    client: reqwest::Client,
}

impl DaemonClient {
    pub fn new(port: u16) -> Self {
        Self {
            base_url: format!("http://127.0.0.1:{}", port),
            client: reqwest::Client::builder()
                .timeout(std::time::Duration::from_secs(10))
                .build()
                .expect("Failed to create HTTP client"),
        }
    }

    pub async fn get<T: DeserializeOwned>(&self, path: &str) -> Result<T, String> {
        let url = format!("{}{}", self.base_url, path);
        let resp = self
            .client
            .get(&url)
            .send()
            .await
            .map_err(|e| format!("Error de conexión con daemon: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Daemon respondió con status {}", resp.status()));
        }

        resp.json::<T>()
            .await
            .map_err(|e| format!("Error deserializando respuesta: {}", e))
    }

    pub async fn post<T: DeserializeOwned, B: serde::Serialize>(
        &self,
        path: &str,
        body: &B,
    ) -> Result<T, String> {
        let url = format!("{}{}", self.base_url, path);
        let resp = self
            .client
            .post(&url)
            .json(body)
            .send()
            .await
            .map_err(|e| format!("Error de conexión con daemon: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Daemon respondió con status {}", resp.status()));
        }

        resp.json::<T>()
            .await
            .map_err(|e| format!("Error deserializando respuesta: {}", e))
    }

    pub async fn post_empty<B: serde::Serialize>(
        &self,
        path: &str,
        body: &B,
    ) -> Result<(), String> {
        let url = format!("{}{}", self.base_url, path);
        let resp = self
            .client
            .post(&url)
            .json(body)
            .send()
            .await
            .map_err(|e| format!("Error de conexión con daemon: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Daemon respondió con status {}", resp.status()));
        }

        Ok(())
    }

    pub async fn put<B: serde::Serialize>(
        &self,
        path: &str,
        body: &B,
    ) -> Result<(), String> {
        let url = format!("{}{}", self.base_url, path);
        let resp = self
            .client
            .put(&url)
            .json(body)
            .send()
            .await
            .map_err(|e| format!("Error de conexión con daemon: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Daemon respondió con status {}", resp.status()));
        }

        Ok(())
    }

    pub async fn delete(&self, path: &str) -> Result<(), String> {
        let url = format!("{}{}", self.base_url, path);
        let resp = self
            .client
            .delete(&url)
            .send()
            .await
            .map_err(|e| format!("Error de conexión con daemon: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Daemon respondió con status {}", resp.status()));
        }

        Ok(())
    }

    pub async fn health_check(&self) -> bool {
        self.get::<serde_json::Value>("/health").await.is_ok()
    }
}
