# Fase 4 — Descripciones IA: Diseño

## Resumen

Generar descripciones automáticas para bloques de actividad usando LLMs configurables (Gemini/Claude/OpenAI). Patrón adaptador, cache en SQLite, generación al cerrar bloque, contexto de usuario personalizable.

## Arquitectura

```
Settings (provider + API key + role + context) → keyring → PUT /config → daemon
                                                                          ↓
Block cerrado → BlockManager._close_current_block()
                    ↓
              AIService.generate(block_data)
                    ↓
              ┌─ cache hit? → usar cache
              └─ cache miss → Provider.generate() → guardar en DB
                                  ↓
                         GeminiProvider / ClaudeProvider / OpenAIProvider
```

## Componentes

### 1. Historial de títulos de ventana
- `BlockManager` acumula `window_titles: list[str]` (únicos, max 20)
- Al cerrar bloque, se guardan en campo `window_titles_json` en tabla blocks
- `context_enricher` añade `last_commit_message` via `git log -1 --format=%s`

### 2. AIService
- Orquestador: construye prompt, llama al provider, guarda resultado
- Cache en SQLite: tabla `ai_cache` (key=hash señales, value=descripción+confidence)
- Sin provider → fallback heurístico
- Errores capturados, nunca bloquea cierre de bloque

### 3. Providers
- `GeminiProvider` — google-generativeai, gemini-2.0-flash
- `ClaudeProvider` — anthropic, claude-haiku-4-5-20251001
- `OpenAIProvider` — openai, gpt-4o-mini
- Todos implementan `DescriptionProvider.generate()`

### 4. Prompt
```
Genera una descripción concisa (1 línea, máx 120 chars) de la actividad
laboral basándote en las señales. Responde SOLO con la descripción.
Idioma: español.

Perfil: {role}
Contexto: {custom_context}

Señales: app={app}, proyecto={project}, rama={branch}, duración={duration}min,
títulos={titles}, último commit="{commit_msg}"
```

### 5. Config usuario
- `ai_provider`: "gemini" | "claude" | "openai" | "none"
- `ai_api_key`: guardada en keyring
- `ai_user_role`: "technical" | "functional" | "other"
- `ai_custom_context`: texto libre

### 6. Endpoints
- `POST /blocks/{id}/generate-description` — regenerar bajo demanda

### 7. Frontend
- SettingsView: sección IA con provider, API key, rol, contexto
- BlockRow: muestra ai_description con ConfidenceBadge
- BlockEditor: botón regenerar descripción
