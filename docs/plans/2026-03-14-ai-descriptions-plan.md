# Fase 4 — Descripciones IA: Plan de Implementación

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Generar descripciones automáticas de bloques de actividad usando LLMs configurables (Gemini/Claude/OpenAI) con cache y contexto de usuario.

**Architecture:** Patrón adaptador con 3 providers LLM intercambiables. AIService orquesta generación al cerrar bloques, con cache en SQLite por hash de señales. Frontend muestra descripciones y permite regenerar.

**Tech Stack:** Python (google-generativeai, anthropic, openai), FastAPI endpoints, Vue 3 + TypeScript frontend, Rust Tauri commands.

---

### Task 1: Ampliar EnrichedContext con last_commit_message

**Files:**
- Modify: `daemon/mimir_daemon/context_enricher.py:16-24` (EnrichedContext dataclass)
- Modify: `daemon/mimir_daemon/context_enricher.py:27-48` (enrich_pid function)
- Test: `daemon/tests/test_context_enricher.py`

**Step 1: Write the failing test**

En `daemon/tests/test_context_enricher.py`, añadir al final:

```python
@pytest.mark.asyncio
async def test_enrich_pid_includes_last_commit(tmp_path, monkeypatch):
    """enrich_pid incluye el último commit message."""
    from mimir_daemon.context_enricher import enrich_pid, invalidate_git_cache, EnrichedContext
    invalidate_git_cache()

    # Crear repo git con un commit
    import subprocess
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "test@test.com"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Test"], check=True, capture_output=True)
    (tmp_path / "file.txt").write_text("hello")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "feat: initial commit"], check=True, capture_output=True)

    # Mock _read_proc_cwd para que devuelva tmp_path
    monkeypatch.setattr("mimir_daemon.context_enricher._read_proc_cwd", lambda pid: str(tmp_path))

    ctx = await enrich_pid(1234)
    assert ctx.last_commit_message == "feat: initial commit"
```

**Step 2: Run test to verify it fails**

Run: `cd /opt/mimir-app/daemon && python -m pytest tests/test_context_enricher.py::test_enrich_pid_includes_last_commit -v`
Expected: FAIL — `EnrichedContext` has no attribute `last_commit_message`

**Step 3: Write minimal implementation**

In `daemon/mimir_daemon/context_enricher.py`, add field to `EnrichedContext`:

```python
@dataclass
class EnrichedContext:
    """Contexto enriquecido de un proceso."""

    cwd: str | None = None
    git_branch: str | None = None
    git_remote: str | None = None
    project_path: str | None = None
    ssh_host: str | None = None
    last_commit_message: str | None = None
    extra: dict[str, str] = field(default_factory=dict)
```

In `enrich_pid`, after getting branch/remote, add:

```python
            ctx.git_branch = branch
            ctx.git_remote = remote
            ctx.last_commit_message = await _get_last_commit_message(str(git_root))
```

Add the helper function after `_get_git_info`:

```python
async def _get_last_commit_message(git_root: str) -> str | None:
    """Obtiene el mensaje del último commit."""
    return await _run_git(git_root, "log", "-1", "--format=%s")
```

**Step 4: Run test to verify it passes**

Run: `cd /opt/mimir-app/daemon && python -m pytest tests/test_context_enricher.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add daemon/mimir_daemon/context_enricher.py daemon/tests/test_context_enricher.py
git commit -m "feat: add last_commit_message to EnrichedContext"
```

---

### Task 2: Historial de títulos de ventana en BlockManager

**Files:**
- Modify: `daemon/mimir_daemon/block_manager.py:17-27` (constructor)
- Modify: `daemon/mimir_daemon/block_manager.py:137-164` (_create_block, _update_current_block)
- Modify: `daemon/mimir_daemon/block_manager.py:197-208` (_close_current_block)
- Modify: `daemon/mimir_daemon/db.py:10-32` (SCHEMA — add column)
- Test: `daemon/tests/test_block_manager.py`

**Step 1: Add `window_titles_json` column to DB schema**

In `daemon/mimir_daemon/db.py`, add after `odoo_entry_id INTEGER,`:

```sql
    window_titles_json TEXT,
```

**Step 2: Write the failing test**

In `daemon/tests/test_block_manager.py`, add:

```python
@pytest.mark.asyncio
async def test_block_tracks_window_titles(db):
    """BlockManager acumula títulos de ventana únicos."""
    import json
    bm = BlockManager(db=db)

    # Simular 3 polls con distintos títulos
    for title in ["models.py — VS Code", "test_models.py — VS Code", "models.py — VS Code"]:
        window = WindowInfo(pid=100, app_name="code", window_title=title)
        ctx = EnrichedContext(project_path="/home/user/project", git_branch="main")
        await bm.process_poll(window, ctx)

    # Cerrar bloque
    await bm._close_current_block()

    blocks = await db.get_blocks_by_date(datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    assert len(blocks) == 1
    titles = json.loads(blocks[0]["window_titles_json"])
    # Solo 2 únicos (el tercero es duplicado)
    assert len(titles) == 2
    assert "models.py — VS Code" in titles
    assert "test_models.py — VS Code" in titles
```

**Step 3: Run test to verify it fails**

Run: `cd /opt/mimir-app/daemon && python -m pytest tests/test_block_manager.py::test_block_tracks_window_titles -v`
Expected: FAIL

**Step 4: Implement window title tracking in BlockManager**

In `daemon/mimir_daemon/block_manager.py`:

Add import at top:
```python
import json
```

In `__init__`, add:
```python
        self._window_titles: list[str] = []
        self._max_titles: int = 20
```

In `_create_block`, after setting `self._current_project`, add:
```python
        self._window_titles = [window.window_title]
```

In `_update_current_block`, before the `await self._db.update_block(...)` call, add:
```python
        if window.window_title not in self._window_titles:
            if len(self._window_titles) < self._max_titles:
                self._window_titles.append(window.window_title)
```

In `_close_current_block`, before setting `self._current_block_id = None`, add:
```python
            if self._window_titles:
                await self._db.update_block(
                    self._current_block_id,
                    window_titles_json=json.dumps(self._window_titles, ensure_ascii=False),
                )
```

After setting `self._current_project = None`, add:
```python
            self._window_titles = []
```

**Step 5: Run test to verify it passes**

Run: `cd /opt/mimir-app/daemon && python -m pytest tests/test_block_manager.py -v`
Expected: ALL PASS

**Step 6: Run full test suite**

Run: `cd /opt/mimir-app/daemon && python -m pytest tests/ -v`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add daemon/mimir_daemon/block_manager.py daemon/mimir_daemon/db.py daemon/tests/test_block_manager.py
git commit -m "feat: track window titles history in blocks"
```

---

### Task 3: Tabla ai_cache en SQLite + AIService base

**Files:**
- Modify: `daemon/mimir_daemon/db.py:10-53` (add ai_cache table to SCHEMA)
- Modify: `daemon/mimir_daemon/db.py` (add ai_cache methods)
- Create: `daemon/mimir_daemon/ai/service.py`
- Test: `daemon/tests/test_ai_service.py`

**Step 1: Add ai_cache table to DB schema**

In `daemon/mimir_daemon/db.py`, add to SCHEMA before the closing `"""`:

```sql
CREATE TABLE IF NOT EXISTS ai_cache (
    signal_hash TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    confidence REAL NOT NULL,
    provider TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

**Step 2: Add cache methods to Database**

In `daemon/mimir_daemon/db.py`, add after `set_preference`:

```python
    # --- AI cache ---

    async def get_ai_cache(self, signal_hash: str) -> dict | None:
        """Obtiene una descripción cacheada por hash de señales."""
        async with self.db.execute(
            "SELECT * FROM ai_cache WHERE signal_hash = ?", (signal_hash,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def set_ai_cache(
        self, signal_hash: str, description: str, confidence: float, provider: str
    ) -> None:
        """Guarda una descripción en la cache."""
        await self.db.execute(
            "INSERT OR REPLACE INTO ai_cache (signal_hash, description, confidence, provider) "
            "VALUES (?, ?, ?, ?)",
            (signal_hash, description, confidence, provider),
        )
        await self.db.commit()
```

**Step 3: Write the failing test for AIService**

Create `daemon/tests/test_ai_service.py`:

```python
"""Tests para AIService."""

import pytest
import pytest_asyncio

from mimir_daemon.db import Database
from mimir_daemon.ai.service import AIService
from mimir_daemon.ai.base import DescriptionProvider, DescriptionRequest, DescriptionResult


class FakeProvider(DescriptionProvider):
    """Provider falso para tests."""

    def __init__(self, response: str = "Desarrollo en proyecto X", confidence: float = 0.85):
        self.response = response
        self.confidence = confidence
        self.call_count = 0

    async def generate(self, request: DescriptionRequest) -> DescriptionResult:
        self.call_count += 1
        return DescriptionResult(description=self.response, confidence=self.confidence)


@pytest_asyncio.fixture
async def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    await database.connect()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_ai_service_generates_description(db):
    """AIService genera descripción usando el provider."""
    provider = FakeProvider()
    service = AIService(db=db, provider=provider)

    request = DescriptionRequest(
        app_name="code",
        window_title="models.py — VS Code",
        project_path="/home/user/mimir-app",
        git_branch="feat/ai",
        git_remote="git@github.com:user/mimir.git",
        duration_minutes=45,
    )
    result = await service.generate(request)
    assert result.description == "Desarrollo en proyecto X"
    assert result.confidence == 0.85
    assert provider.call_count == 1


@pytest.mark.asyncio
async def test_ai_service_uses_cache(db):
    """AIService devuelve resultado cacheado en la segunda llamada."""
    provider = FakeProvider()
    service = AIService(db=db, provider=provider)

    request = DescriptionRequest(
        app_name="code",
        window_title="models.py — VS Code",
        project_path="/home/user/mimir-app",
        git_branch="feat/ai",
        git_remote=None,
        duration_minutes=45,
    )
    result1 = await service.generate(request)
    result2 = await service.generate(request)

    assert result1.description == result2.description
    assert result2.cached is True
    assert provider.call_count == 1  # Solo se llamo una vez


@pytest.mark.asyncio
async def test_ai_service_fallback_without_provider(db):
    """AIService usa heurístico si no hay provider."""
    service = AIService(db=db, provider=None)

    request = DescriptionRequest(
        app_name="code",
        window_title="server.py — VS Code",
        project_path="/home/user/mimir-app",
        git_branch="feat/ai",
        git_remote=None,
        duration_minutes=30,
    )
    result = await service.generate(request)
    assert result.description  # No vacío
    assert result.confidence == 0.5  # Confianza baja del heurístico


@pytest.mark.asyncio
async def test_ai_service_handles_provider_error(db):
    """AIService hace fallback si el provider falla."""

    class FailingProvider(DescriptionProvider):
        async def generate(self, request):
            raise RuntimeError("API error")

    service = AIService(db=db, provider=FailingProvider())

    request = DescriptionRequest(
        app_name="firefox",
        window_title="Google — Firefox",
        project_path=None,
        git_branch=None,
        git_remote=None,
        duration_minutes=15,
    )
    result = await service.generate(request)
    assert result.description  # Fallback heurístico
    assert result.confidence == 0.5
```

**Step 4: Run test to verify it fails**

Run: `cd /opt/mimir-app/daemon && python -m pytest tests/test_ai_service.py -v`
Expected: FAIL — module `mimir_daemon.ai.service` not found

**Step 5: Implement AIService**

Create `daemon/mimir_daemon/ai/service.py`:

```python
"""Servicio orquestador de descripciones IA."""

import hashlib
import logging

from ..db import Database
from .base import DescriptionProvider, DescriptionRequest, DescriptionResult

logger = logging.getLogger(__name__)


class AIService:
    """Orquesta la generación de descripciones IA con cache."""

    def __init__(self, db: Database, provider: DescriptionProvider | None = None) -> None:
        self._db = db
        self._provider = provider

    @property
    def provider(self) -> DescriptionProvider | None:
        return self._provider

    @provider.setter
    def provider(self, value: DescriptionProvider | None) -> None:
        self._provider = value

    def _compute_hash(self, request: DescriptionRequest) -> str:
        """Computa hash de las señales para cache."""
        signals = (
            f"{request.app_name}|{request.window_title}|"
            f"{request.project_path}|{request.git_branch}"
        )
        return hashlib.sha256(signals.encode()).hexdigest()[:16]

    async def generate(self, request: DescriptionRequest) -> DescriptionResult:
        """Genera descripción: cache -> provider -> heurístico."""
        cache_key = self._compute_hash(request)

        # 1. Buscar en cache
        cached = await self._db.get_ai_cache(cache_key)
        if cached:
            return DescriptionResult(
                description=cached["description"],
                confidence=cached["confidence"],
                cached=True,
            )

        # 2. Intentar provider
        if self._provider:
            try:
                result = await self._provider.generate(request)
                # Guardar en cache
                provider_name = type(self._provider).__name__
                await self._db.set_ai_cache(
                    cache_key, result.description, result.confidence, provider_name
                )
                return result
            except Exception as e:
                logger.error("Error en provider IA: %s", e)

        # 3. Fallback heurístico
        description = self._heuristic(request)
        return DescriptionResult(description=description, confidence=0.5)

    def _heuristic(self, request: DescriptionRequest) -> str:
        """Genera descripción heurística como fallback."""
        parts = []
        if request.git_branch and request.project_path:
            project = request.project_path.rsplit("/", 1)[-1]
            parts.append(f"Trabajo en {project}")
            if request.git_branch not in ("main", "master"):
                parts.append(f"rama {request.git_branch}")
        elif request.app_name:
            parts.append(f"Usando {request.app_name}")

        if request.window_title:
            title_parts = request.window_title.split(" - ")
            if len(title_parts) > 1:
                parts.append(title_parts[0][:50])

        return " — ".join(parts) if parts else f"Actividad en {request.app_name}"
```

**Step 6: Run test to verify it passes**

Run: `cd /opt/mimir-app/daemon && python -m pytest tests/test_ai_service.py -v`
Expected: ALL PASS

**Step 7: Run full test suite**

Run: `cd /opt/mimir-app/daemon && python -m pytest tests/ -v`
Expected: ALL PASS

**Step 8: Commit**

```bash
git add daemon/mimir_daemon/db.py daemon/mimir_daemon/ai/service.py daemon/tests/test_ai_service.py
git commit -m "feat: add AIService with cache and fallback heuristic"
```

---

### Task 4: Implementar los 3 providers LLM

**Files:**
- Modify: `daemon/mimir_daemon/ai/gemini.py` (rewrite)
- Create: `daemon/mimir_daemon/ai/claude_provider.py`
- Create: `daemon/mimir_daemon/ai/openai_provider.py`
- Modify: `daemon/mimir_daemon/ai/base.py:6-17` (add fields to DescriptionRequest)
- Modify: `daemon/pyproject.toml` (add dependencies)
- Test: `daemon/tests/test_ai_providers.py`

**Step 1: Add new fields to DescriptionRequest**

In `daemon/mimir_daemon/ai/base.py`, update `DescriptionRequest`:

```python
@dataclass
class DescriptionRequest:
    """Señales de un bloque para generar descripción."""

    app_name: str
    window_title: str
    project_path: str | None
    git_branch: str | None
    git_remote: str | None
    duration_minutes: float
    window_titles: list[str] | None = None
    last_commit_message: str | None = None
    user_role: str = "technical"
    user_context: str = ""
```

**Step 2: Add SDK dependencies to pyproject.toml**

In `daemon/pyproject.toml`, add to `dependencies`:

```toml
    "google-generativeai>=0.8.0",
    "anthropic>=0.40.0",
    "openai>=1.50.0",
```

Run: `cd /opt/mimir-app/daemon && pip install -e ".[dev]"`

**Step 3: Write tests for providers**

Create `daemon/tests/test_ai_providers.py`:

```python
"""Tests para providers IA (con mocks de SDKs)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mimir_daemon.ai.base import DescriptionRequest


def _make_request(**overrides) -> DescriptionRequest:
    defaults = dict(
        app_name="code",
        window_title="server.py — VS Code",
        project_path="/home/user/mimir-app",
        git_branch="feat/ai",
        git_remote=None,
        duration_minutes=45,
        window_titles=["server.py — VS Code", "test_server.py — VS Code"],
        last_commit_message="fix: retry logic",
        user_role="technical",
        user_context="Backend developer",
    )
    defaults.update(overrides)
    return DescriptionRequest(**defaults)


@pytest.mark.asyncio
async def test_gemini_provider_builds_prompt_and_calls_api():
    """GeminiProvider construye prompt correcto y llama a la API."""
    from mimir_daemon.ai.gemini import GeminiProvider

    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Desarrollo de lógica de reintento en servidor"
    mock_model.generate_content_async = AsyncMock(return_value=mock_response)

    with patch("mimir_daemon.ai.gemini.genai") as mock_genai:
        mock_genai.GenerativeModel.return_value = mock_model
        provider = GeminiProvider(api_key="test-key")
        result = await provider.generate(_make_request())

    assert result.description == "Desarrollo de lógica de reintento en servidor"
    assert result.confidence == 0.8
    mock_model.generate_content_async.assert_called_once()
    # Verificar que el prompt contiene las señales
    call_args = mock_model.generate_content_async.call_args[0][0]
    assert "server.py" in call_args
    assert "feat/ai" in call_args
    assert "technical" in call_args


@pytest.mark.asyncio
async def test_claude_provider_builds_prompt_and_calls_api():
    """ClaudeProvider construye prompt correcto y llama a la API."""
    from mimir_daemon.ai.claude_provider import ClaudeProvider

    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Implementación de reintentos en API")]
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    with patch("mimir_daemon.ai.claude_provider.anthropic.AsyncAnthropic", return_value=mock_client):
        provider = ClaudeProvider(api_key="test-key")
        result = await provider.generate(_make_request())

    assert result.description == "Implementación de reintentos en API"
    assert result.confidence == 0.8
    mock_client.messages.create.assert_called_once()


@pytest.mark.asyncio
async def test_openai_provider_builds_prompt_and_calls_api():
    """OpenAIProvider construye prompt correcto y llama a la API."""
    from mimir_daemon.ai.openai_provider import OpenAIProvider

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Corrección de lógica de sincronización"
    mock_response.choices = [mock_choice]
    mock_client.chat = MagicMock()
    mock_client.chat.completions = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch("mimir_daemon.ai.openai_provider.openai.AsyncOpenAI", return_value=mock_client):
        provider = OpenAIProvider(api_key="test-key")
        result = await provider.generate(_make_request())

    assert result.description == "Corrección de lógica de sincronización"
    assert result.confidence == 0.8
    mock_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_gemini_provider_handles_empty_response():
    """GeminiProvider maneja respuesta vacía."""
    from mimir_daemon.ai.gemini import GeminiProvider

    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = ""
    mock_model.generate_content_async = AsyncMock(return_value=mock_response)

    with patch("mimir_daemon.ai.gemini.genai") as mock_genai:
        mock_genai.GenerativeModel.return_value = mock_model
        provider = GeminiProvider(api_key="test-key")
        result = await provider.generate(_make_request())

    # Debe devolver algo aunque la API devuelva vacío
    assert result.description  # fallback
    assert result.confidence < 0.8
```

**Step 4: Run tests to verify they fail**

Run: `cd /opt/mimir-app/daemon && python -m pytest tests/test_ai_providers.py -v`
Expected: FAIL — imports broken

**Step 5: Implement GeminiProvider**

Rewrite `daemon/mimir_daemon/ai/gemini.py`:

```python
"""Proveedor de descripciones IA usando Google Gemini."""

import logging

import google.generativeai as genai

from .base import DescriptionProvider, DescriptionRequest, DescriptionResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Genera una descripción concisa (1 línea, máximo 120 caracteres) de la actividad "
    "laboral basándote en las señales proporcionadas. Responde SOLO con la descripción, "
    "sin explicaciones ni formato adicional. Idioma: español."
)


def _build_user_prompt(request: DescriptionRequest) -> str:
    """Construye el prompt de usuario con las señales del bloque."""
    parts = [f"App: {request.app_name}"]
    if request.project_path:
        project = request.project_path.rsplit("/", 1)[-1]
        parts.append(f"Proyecto: {project}")
    if request.git_branch:
        parts.append(f"Rama: {request.git_branch}")
    parts.append(f"Duración: {request.duration_minutes:.0f}min")
    if request.window_titles:
        titles = ", ".join(request.window_titles[:10])
        parts.append(f"Archivos/ventanas: {titles}")
    elif request.window_title:
        parts.append(f"Ventana: {request.window_title}")
    if request.last_commit_message:
        parts.append(f'Último commit: "{request.last_commit_message}"')

    prompt = f"Perfil: {request.user_role}\n"
    if request.user_context:
        prompt += f"Contexto: {request.user_context}\n"
    prompt += "\nSeñales:\n" + "\n".join(f"- {p}" for p in parts)
    return prompt


class GeminiProvider(DescriptionProvider):
    """Proveedor de descripciones usando Google Gemini API."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            model_name=model,
            system_instruction=SYSTEM_PROMPT,
        )

    async def generate(self, request: DescriptionRequest) -> DescriptionResult:
        """Genera descripción con Gemini."""
        prompt = _build_user_prompt(request)
        logger.debug("Gemini prompt: %s", prompt)

        response = await self._model.generate_content_async(prompt)
        text = (response.text or "").strip()

        if not text:
            logger.warning("Gemini devolvió respuesta vacía")
            return DescriptionResult(
                description=f"Actividad en {request.app_name}",
                confidence=0.3,
            )

        # Truncar a 120 chars si el modelo se pasó
        if len(text) > 120:
            text = text[:117] + "..."

        return DescriptionResult(description=text, confidence=0.8)
```

**Step 6: Implement ClaudeProvider**

Create `daemon/mimir_daemon/ai/claude_provider.py`:

```python
"""Proveedor de descripciones IA usando Anthropic Claude."""

import logging

import anthropic

from .base import DescriptionProvider, DescriptionRequest, DescriptionResult
from .gemini import SYSTEM_PROMPT, _build_user_prompt

logger = logging.getLogger(__name__)


class ClaudeProvider(DescriptionProvider):
    """Proveedor de descripciones usando Anthropic Claude API."""

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001") -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def generate(self, request: DescriptionRequest) -> DescriptionResult:
        """Genera descripción con Claude."""
        prompt = _build_user_prompt(request)
        logger.debug("Claude prompt: %s", prompt)

        message = await self._client.messages.create(
            model=self._model,
            max_tokens=150,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        text = (message.content[0].text or "").strip() if message.content else ""

        if not text:
            logger.warning("Claude devolvió respuesta vacía")
            return DescriptionResult(
                description=f"Actividad en {request.app_name}",
                confidence=0.3,
            )

        if len(text) > 120:
            text = text[:117] + "..."

        return DescriptionResult(description=text, confidence=0.8)
```

**Step 7: Implement OpenAIProvider**

Create `daemon/mimir_daemon/ai/openai_provider.py`:

```python
"""Proveedor de descripciones IA usando OpenAI."""

import logging

import openai

from .base import DescriptionProvider, DescriptionRequest, DescriptionResult
from .gemini import SYSTEM_PROMPT, _build_user_prompt

logger = logging.getLogger(__name__)


class OpenAIProvider(DescriptionProvider):
    """Proveedor de descripciones usando OpenAI API."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self._client = openai.AsyncOpenAI(api_key=api_key)
        self._model = model

    async def generate(self, request: DescriptionRequest) -> DescriptionResult:
        """Genera descripción con OpenAI."""
        prompt = _build_user_prompt(request)
        logger.debug("OpenAI prompt: %s", prompt)

        response = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=150,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        text = (response.choices[0].message.content or "").strip() if response.choices else ""

        if not text:
            logger.warning("OpenAI devolvió respuesta vacía")
            return DescriptionResult(
                description=f"Actividad en {request.app_name}",
                confidence=0.3,
            )

        if len(text) > 120:
            text = text[:117] + "..."

        return DescriptionResult(description=text, confidence=0.8)
```

**Step 8: Run tests to verify they pass**

Run: `cd /opt/mimir-app/daemon && python -m pytest tests/test_ai_providers.py -v`
Expected: ALL PASS

**Step 9: Run full test suite**

Run: `cd /opt/mimir-app/daemon && python -m pytest tests/ -v`
Expected: ALL PASS

**Step 10: Commit**

```bash
git add daemon/mimir_daemon/ai/ daemon/tests/test_ai_providers.py daemon/pyproject.toml
git commit -m "feat: add Gemini, Claude, and OpenAI description providers"
```

---

### Task 5: Integrar AIService en BlockManager y server.py

**Files:**
- Modify: `daemon/mimir_daemon/block_manager.py` (add ai_service, call on close)
- Modify: `daemon/mimir_daemon/server.py` (add ai_service param, generate-description endpoint)
- Modify: `daemon/mimir_daemon/main.py` (create and wire AIService)
- Test: `daemon/tests/test_server.py`

**Step 1: Write failing tests**

Add to `daemon/tests/test_server.py`:

```python
@pytest.mark.asyncio
async def test_generate_description_endpoint(client, db):
    """POST /blocks/{id}/generate-description genera descripción IA."""
    now = datetime.now(timezone.utc).isoformat()
    block_id = await db.create_block(
        start_time=now, end_time=now, duration_minutes=30,
        app_name="code", window_title="models.py — VS Code",
        project_path="/home/user/project", git_branch="feat/ai",
        status="closed",
    )
    resp = await client.post(f"/blocks/{block_id}/generate-description")
    assert resp.status_code == 200
    data = resp.json()
    assert "description" in data
    assert "confidence" in data

    # Verificar que se guardó en el bloque
    block = await db.get_block_by_id(block_id)
    assert block["ai_description"] is not None


@pytest.mark.asyncio
async def test_generate_description_block_not_found(client):
    """POST /blocks/{id}/generate-description devuelve 404."""
    resp = await client.post("/blocks/9999/generate-description")
    assert resp.status_code == 404
```

**Step 2: Run tests to verify they fail**

Run: `cd /opt/mimir-app/daemon && python -m pytest tests/test_server.py::test_generate_description_endpoint -v`
Expected: FAIL — endpoint not found (404 or 405)

**Step 3: Add AIService to BlockManager**

In `daemon/mimir_daemon/block_manager.py`:

Update `__init__` signature:
```python
    def __init__(
        self,
        db: Database,
        inherit_threshold: int = 900,
        ai_service: "AIService | None" = None,
    ) -> None:
```

Add: `self._ai_service = ai_service`

Add import at top:
```python
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .ai.service import AIService
```

In `_close_current_block`, after saving window_titles_json and before setting `self._current_block_id = None`, add:

```python
            # Generar descripción IA
            if self._ai_service:
                try:
                    block = await self._db.get_block_by_id(self._current_block_id)
                    if block and not block.get("user_description"):
                        from .ai.base import DescriptionRequest
                        request = DescriptionRequest(
                            app_name=block.get("app_name", ""),
                            window_title=block.get("window_title", ""),
                            project_path=block.get("project_path"),
                            git_branch=block.get("git_branch"),
                            git_remote=block.get("git_remote"),
                            duration_minutes=block.get("duration_minutes", 0),
                            window_titles=json.loads(block["window_titles_json"])
                            if block.get("window_titles_json") else None,
                        )
                        result = await self._ai_service.generate(request)
                        await self._db.update_block(
                            self._current_block_id,
                            ai_description=result.description,
                            ai_confidence=result.confidence,
                        )
                        logger.info(
                            "Descripción IA para bloque #%d: %s (%.1f)",
                            self._current_block_id, result.description, result.confidence,
                        )
                except Exception as e:
                    logger.error("Error generando descripción IA: %s", e)
```

**Step 4: Add AIService + endpoint to server.py**

In `daemon/mimir_daemon/server.py`, update `create_app` signature:

```python
def create_app(
    db: Database,
    poller: Poller,
    registry: IntegrationRegistry | None = None,
    ai_service: "AIService | None" = None,
    version: str = "0.1.0",
) -> FastAPI:
```

Add import at top:
```python
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .ai.service import AIService
```

Add the endpoint before `# --- Odoo ---`:

```python
    @app.post("/blocks/{block_id}/generate-description")
    async def generate_description(block_id: int) -> dict:
        """Genera o regenera descripción IA para un bloque."""
        block = await db.get_block_by_id(block_id)
        if not block:
            raise HTTPException(404, "Bloque no encontrado")

        from .ai.base import DescriptionRequest
        _ai = ai_service
        if not _ai:
            # Crear servicio sin provider (solo heurístico)
            from .ai.service import AIService as _AIS
            _ai = _AIS(db=db, provider=None)

        request = DescriptionRequest(
            app_name=block.get("app_name", ""),
            window_title=block.get("window_title", ""),
            project_path=block.get("project_path"),
            git_branch=block.get("git_branch"),
            git_remote=block.get("git_remote"),
            duration_minutes=block.get("duration_minutes", 0),
            window_titles=json.loads(block["window_titles_json"])
            if block.get("window_titles_json") else None,
        )

        result = await _ai.generate(request)
        await db.update_block(
            block_id,
            ai_description=result.description,
            ai_confidence=result.confidence,
        )

        return {
            "description": result.description,
            "confidence": result.confidence,
            "cached": result.cached,
        }
```

**Step 5: Update test fixture to include ai_service**

In `daemon/tests/test_server.py`, update the `app` fixture:

```python
@pytest.fixture
def app(db, registry):
    from mimir_daemon.ai.service import AIService
    config = DaemonConfig(polling_interval=60)
    platform = MockPlatform()
    block_manager = BlockManager(db=db)
    poller = Poller(config=config, db=db, platform=platform, block_manager=block_manager)
    ai_service = AIService(db=db, provider=None)  # Heurístico para tests
    return create_app(db=db, poller=poller, registry=registry, ai_service=ai_service)
```

**Step 6: Run tests to verify they pass**

Run: `cd /opt/mimir-app/daemon && python -m pytest tests/test_server.py -v`
Expected: ALL PASS

**Step 7: Wire AIService in main.py**

In `daemon/mimir_daemon/main.py`, add import:

```python
from .ai.service import AIService
```

In `run_daemon`, after creating `block_manager` and before `recover_open_blocks`:

```python
    # Servicio IA (se configura el provider via PUT /config)
    ai_service = AIService(db=db, provider=None)
    block_manager = BlockManager(
        db=db,
        inherit_threshold=config.inherit_threshold,
        ai_service=ai_service,
    )
```

Update `create_app` call:

```python
    app = create_app(db=db, poller=poller, registry=registry, ai_service=ai_service, version=VERSION)
```

**Step 8: Run full test suite**

Run: `cd /opt/mimir-app/daemon && python -m pytest tests/ -v`
Expected: ALL PASS

**Step 9: Commit**

```bash
git add daemon/mimir_daemon/block_manager.py daemon/mimir_daemon/server.py daemon/mimir_daemon/main.py daemon/tests/test_server.py
git commit -m "feat: integrate AIService into block lifecycle and add generate-description endpoint"
```

---

### Task 6: Configuración IA en daemon (PUT /config)

**Files:**
- Modify: `daemon/mimir_daemon/server.py` (AppConfigRequest + provider setup)
- Test: `daemon/tests/test_server.py`

**Step 1: Write the failing test**

Add to `daemon/tests/test_server.py`:

```python
@pytest.mark.asyncio
async def test_put_config_ai_provider(client):
    """PUT /config con ai_provider configura el servicio IA."""
    resp = await client.put("/config", json={
        "odoo_url": "",
        "odoo_version": "v16",
        "odoo_db": "",
        "odoo_username": "",
        "odoo_token": "",
        "gitlab_url": "",
        "gitlab_token": "",
        "ai_provider": "none",
        "ai_api_key": "",
        "ai_user_role": "technical",
        "ai_custom_context": "Desarrollo backend en Python",
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_config_no_ai_key_exposed(client):
    """GET /config no expone ai_api_key."""
    await client.put("/config", json={
        "odoo_url": "",
        "odoo_version": "v16",
        "odoo_db": "",
        "odoo_username": "",
        "odoo_token": "",
        "gitlab_url": "",
        "gitlab_token": "",
        "ai_provider": "gemini",
        "ai_api_key": "secret-ai-key",
        "ai_user_role": "functional",
        "ai_custom_context": "",
    })
    resp = await client.get("/config")
    data = resp.json()
    assert "ai_api_key" not in data
    assert data.get("ai_provider") == "gemini"
    assert data.get("ai_user_role") == "functional"
```

**Step 2: Run tests to verify they fail**

Run: `cd /opt/mimir-app/daemon && python -m pytest tests/test_server.py::test_put_config_ai_provider -v`
Expected: FAIL (422 validation error — unexpected fields)

**Step 3: Update AppConfigRequest and config handler**

In `daemon/mimir_daemon/server.py`, update `AppConfigRequest`:

```python
    class AppConfigRequest(BaseModel):
        """Configuracion de la app recibida desde Tauri."""
        odoo_url: str = ""
        odoo_version: str = "v16"
        odoo_db: str = ""
        odoo_username: str = ""
        odoo_token: str = ""
        gitlab_url: str = ""
        gitlab_token: str = ""
        ai_provider: str = "none"
        ai_api_key: str = ""
        ai_user_role: str = "technical"
        ai_custom_context: str = ""
```

In `update_config`, after the Odoo configuration block and before saving to preferences, add:

```python
        # Configurar provider IA
        if ai_service and req.ai_provider != "none" and req.ai_api_key:
            try:
                if req.ai_provider == "gemini":
                    from .ai.gemini import GeminiProvider
                    ai_service.provider = GeminiProvider(api_key=req.ai_api_key)
                elif req.ai_provider == "claude":
                    from .ai.claude_provider import ClaudeProvider
                    ai_service.provider = ClaudeProvider(api_key=req.ai_api_key)
                elif req.ai_provider == "openai":
                    from .ai.openai_provider import OpenAIProvider
                    ai_service.provider = OpenAIProvider(api_key=req.ai_api_key)
                logger.info("Provider IA configurado: %s", req.ai_provider)
            except Exception as e:
                logger.error("Error configurando provider IA: %s", e)
        elif ai_service and req.ai_provider == "none":
            ai_service.provider = None
            logger.info("Provider IA desactivado")
```

Also update the `get_config` safe_config filter to also exclude `ai_api_key` (already handled by `"token" not in k` — but `ai_api_key` contains "key" not "token"). Add explicit filter:

```python
        safe_config = {
            k: v for k, v in _app_config.items()
            if "token" not in k and "password" not in k and k != "ai_api_key"
        }
```

Add `ai_configured` flag:

```python
        safe_config["ai_configured"] = bool(
            _app_config.get("ai_provider", "none") != "none"
            and _app_config.get("ai_api_key")
        )
```

**Step 4: Run tests to verify they pass**

Run: `cd /opt/mimir-app/daemon && python -m pytest tests/test_server.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add daemon/mimir_daemon/server.py daemon/tests/test_server.py
git commit -m "feat: add AI provider configuration via PUT /config"
```

---

### Task 7: Frontend — tipos y api.ts

**Files:**
- Modify: `src/lib/types.ts` (add AI fields to AppConfig)
- Modify: `src/lib/api.ts` (add generateDescription)

**Step 1: Update AppConfig type**

In `src/lib/types.ts`, add to `AppConfig` interface:

```typescript
  ai_provider: 'gemini' | 'claude' | 'openai' | 'none';
  ai_api_key_stored: boolean;
  ai_user_role: 'technical' | 'functional' | 'other';
  ai_custom_context: string;
```

**Step 2: Update DEFAULT_CONFIG in config store**

In `src/stores/config.ts`, add to `DEFAULT_CONFIG`:

```typescript
  ai_provider: 'none',
  ai_api_key_stored: false,
  ai_user_role: 'technical',
  ai_custom_context: '',
```

**Step 3: Add API methods**

In `src/lib/api.ts`, add to `api` object:

```typescript
  async generateDescription(blockId: number) {
    if (await isTauri()) return tauriInvoke('generate_block_description', { blockId });
    return httpPost(`/blocks/${blockId}/generate-description`);
  },
```

Also update the `getConfig` browser fallback to include AI defaults:

```typescript
      ai_provider: 'none',
      ai_api_key_stored: false,
      ai_user_role: 'technical',
      ai_custom_context: '',
```

**Step 4: Add AI token methods to config store**

In `src/stores/config.ts`, add functions:

```typescript
  async function setAIToken(token: string) {
    await api.storeCredential('ai', token);
    config.value.ai_api_key_stored = true;
    await api.saveConfig(config.value);
  }

  async function deleteAIToken() {
    await api.deleteCredential('ai');
    config.value.ai_api_key_stored = false;
    await api.saveConfig(config.value);
  }
```

And add them to the return block.

**Step 5: Verify TypeScript**

Run: `cd /opt/mimir-app && npx vue-tsc --noEmit`
Expected: 0 errors

**Step 6: Commit**

```bash
git add src/lib/types.ts src/lib/api.ts src/stores/config.ts
git commit -m "feat: add AI config types and API methods to frontend"
```

---

### Task 8: Frontend — SettingsView sección IA

**Files:**
- Modify: `src/views/SettingsView.vue`

**Step 1: Add AI section to template**

In `src/views/SettingsView.vue`, add script refs:

```typescript
const aiToken = ref('');
```

Add function:

```typescript
async function clearAIToken() {
  try {
    await configStore.deleteAIToken();
    message.value = 'API key IA eliminada';
    messageType.value = 'success';
  } catch (e) {
    message.value = `Error: ${e}`;
    messageType.value = 'error';
  }
}
```

In `saveConfig`, add AI token handling alongside the other tokens:

```typescript
    if (aiToken.value) {
      await configStore.setAIToken(aiToken.value);
      aiToken.value = '';
    }
```

Add this fieldset in the template, after the Odoo fieldset and before General:

```html
      <!-- Inteligencia Artificial -->
      <fieldset class="settings-group">
        <legend>Inteligencia Artificial</legend>
        <label class="field">
          <span>Proveedor</span>
          <select v-model="configStore.config.ai_provider">
            <option value="none">Desactivado</option>
            <option value="gemini">Google Gemini</option>
            <option value="claude">Anthropic Claude</option>
            <option value="openai">OpenAI</option>
          </select>
        </label>
        <div class="field" v-if="configStore.config.ai_provider !== 'none'">
          <span>API Key</span>
          <div class="token-field">
            <input type="password" v-model="aiToken"
              :placeholder="configStore.config.ai_api_key_stored ? '***** (guardada en keyring)' : 'API key del proveedor'" />
            <button
              v-if="configStore.config.ai_api_key_stored"
              type="button"
              class="btn btn-danger btn-sm"
              @click="clearAIToken"
              title="Eliminar API key"
            >
              Eliminar
            </button>
          </div>
        </div>
        <label class="field" v-if="configStore.config.ai_provider !== 'none'">
          <span>Perfil de usuario</span>
          <select v-model="configStore.config.ai_user_role">
            <option value="technical">Tecnico</option>
            <option value="functional">Funcional</option>
            <option value="other">Otro</option>
          </select>
        </label>
        <label class="field" v-if="configStore.config.ai_provider !== 'none'">
          <span>Contexto adicional</span>
          <textarea
            v-model="configStore.config.ai_custom_context"
            rows="2"
            placeholder="Ej: Desarrollador backend en equipo de facturacion Odoo, módulos account y sale"
            style="flex:1; background:var(--bg-card); color:var(--text-primary); border:1px solid var(--border); border-radius:4px; padding:6px 10px; font-size:13px; font-family:inherit; resize:vertical;"
          ></textarea>
        </label>
        <div class="field-hint" v-if="configStore.config.ai_provider !== 'none'">
          Las descripciones se generan automaticamente al cerrar cada bloque de actividad.
        </div>
      </fieldset>
```

**Step 2: Verify TypeScript**

Run: `cd /opt/mimir-app && npx vue-tsc --noEmit`
Expected: 0 errors

**Step 3: Commit**

```bash
git add src/views/SettingsView.vue
git commit -m "feat: add AI settings section with provider, role, and context"
```

---

### Task 9: Frontend — botón regenerar en BlockEditor

**Files:**
- Modify: `src/components/blocks/BlockEditor.vue`

**Step 1: Add regenerate functionality**

In `src/components/blocks/BlockEditor.vue`, add:

Script:
```typescript
const generating = ref(false);

async function regenerateDescription() {
  generating.value = true;
  try {
    const result = await api.generateDescription(props.block.id) as { description: string; confidence: number };
    description.value = result.description;
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : String(e);
  } finally {
    generating.value = false;
  }
}
```

Template — add button after the textarea in the description field:

```html
      <label class="field">
        <span class="field-label">Descripcion</span>
        <div style="flex:1; display:flex; flex-direction:column; gap:4px;">
          <textarea v-model="description" rows="2" placeholder="Describe la actividad..."></textarea>
          <button
            type="button"
            class="btn-regenerate"
            @click="regenerateDescription"
            :disabled="generating"
            title="Generar descripcion con IA"
          >
            {{ generating ? 'Generando...' : 'Generar con IA' }}
          </button>
        </div>
      </label>
```

Style:
```css
.btn-regenerate {
  align-self: flex-start;
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 11px;
  cursor: pointer;
}

.btn-regenerate:hover:not(:disabled) {
  color: var(--accent);
  border-color: var(--accent);
}

.btn-regenerate:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

**Step 2: Verify TypeScript**

Run: `cd /opt/mimir-app && npx vue-tsc --noEmit`
Expected: 0 errors

**Step 3: Commit**

```bash
git add src/components/blocks/BlockEditor.vue
git commit -m "feat: add AI description regenerate button in BlockEditor"
```

---

### Task 10: Rust — Tauri command para generate-description

**Files:**
- Modify: `src-tauri/src/commands/daemon.rs`
- Modify: `src-tauri/src/lib.rs` (register command)

**Step 1: Add Tauri command**

In `src-tauri/src/commands/daemon.rs`, add:

```rust
#[tauri::command]
pub async fn generate_block_description(block_id: i64) -> Result<serde_json::Value, String> {
    get_client()
        .post_json::<serde_json::Value, _>(
            &format!("/blocks/{}/generate-description", block_id),
            &(),
        )
        .await
}
```

**Step 2: Register in lib.rs**

In `src-tauri/src/lib.rs`, add `generate_block_description` to the `invoke_handler` list.

**Step 3: Add AI fields to push_config_to_daemon**

In `src-tauri/src/commands/daemon.rs`, update `DaemonConfigPayload` inside `push_config_to_daemon`:

```rust
    #[derive(serde::Serialize)]
    struct DaemonConfigPayload {
        odoo_url: String,
        odoo_version: String,
        odoo_db: String,
        odoo_username: String,
        odoo_token: String,
        gitlab_url: String,
        gitlab_token: String,
        ai_provider: String,
        ai_api_key: String,
        ai_user_role: String,
        ai_custom_context: String,
    }
```

Update `AppConfig` struct (in `commands/config.rs`) to include the new fields, and update the payload construction:

```rust
        ai_provider: config.ai_provider,
        ai_api_key: read_keyring_token("ai"),
        ai_user_role: config.ai_user_role,
        ai_custom_context: config.ai_custom_context,
```

**Step 4: Verify Rust compiles**

Run: `cd /opt/mimir-app/src-tauri && cargo check`
Expected: OK (may have warnings)

**Step 5: Commit**

```bash
git add src-tauri/src/commands/daemon.rs src-tauri/src/commands/config.rs src-tauri/src/lib.rs
git commit -m "feat: add Tauri command for AI description generation and config"
```

---

### Task 11: Pasar user_role y user_context al generar descripciones

**Files:**
- Modify: `daemon/mimir_daemon/server.py` (pass role/context to DescriptionRequest)
- Modify: `daemon/mimir_daemon/block_manager.py` (pass role/context from config)
- Test: `daemon/tests/test_server.py`

**Step 1: Write test**

Add to `daemon/tests/test_server.py`:

```python
@pytest.mark.asyncio
async def test_generate_description_uses_user_context(client, db):
    """POST /blocks/{id}/generate-description respeta user_role y custom_context."""
    # Configurar perfil de usuario
    await client.put("/config", json={
        "odoo_url": "", "odoo_version": "v16", "odoo_db": "", "odoo_username": "",
        "odoo_token": "", "gitlab_url": "", "gitlab_token": "",
        "ai_provider": "none", "ai_api_key": "",
        "ai_user_role": "functional", "ai_custom_context": "Consultor ERP",
    })

    now = datetime.now(timezone.utc).isoformat()
    block_id = await db.create_block(
        start_time=now, end_time=now, duration_minutes=30,
        app_name="firefox", window_title="Odoo — Facturas",
        status="closed",
    )
    resp = await client.post(f"/blocks/{block_id}/generate-description")
    assert resp.status_code == 200
    data = resp.json()
    assert data["description"]  # Non-empty
```

**Step 2: Update generate_description endpoint**

In the `generate_description` endpoint in `server.py`, pass user role and context from `_app_config`:

```python
        request = DescriptionRequest(
            app_name=block.get("app_name", ""),
            window_title=block.get("window_title", ""),
            project_path=block.get("project_path"),
            git_branch=block.get("git_branch"),
            git_remote=block.get("git_remote"),
            duration_minutes=block.get("duration_minutes", 0),
            window_titles=json.loads(block["window_titles_json"])
            if block.get("window_titles_json") else None,
            user_role=_app_config.get("ai_user_role", "technical"),
            user_context=_app_config.get("ai_custom_context", ""),
        )
```

Do the same in `block_manager.py` — but since BlockManager doesn't have access to app_config, the simplest approach is to store `ai_user_role` and `ai_custom_context` on the AIService:

In `daemon/mimir_daemon/ai/service.py`, add to `__init__`:

```python
        self.user_role: str = "technical"
        self.user_context: str = ""
```

Update `generate` to set these on the request:

```python
        # Enriquecer request con contexto de usuario
        request = DescriptionRequest(
            app_name=request.app_name,
            window_title=request.window_title,
            project_path=request.project_path,
            git_branch=request.git_branch,
            git_remote=request.git_remote,
            duration_minutes=request.duration_minutes,
            window_titles=request.window_titles,
            last_commit_message=request.last_commit_message,
            user_role=request.user_role or self.user_role,
            user_context=request.user_context or self.user_context,
        )
```

In `server.py` `update_config`, after setting the AI provider, set the user context:

```python
        if ai_service:
            ai_service.user_role = req.ai_user_role
            ai_service.user_context = req.ai_custom_context
```

**Step 3: Run tests**

Run: `cd /opt/mimir-app/daemon && python -m pytest tests/ -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add daemon/mimir_daemon/ai/service.py daemon/mimir_daemon/server.py daemon/mimir_daemon/block_manager.py daemon/tests/test_server.py
git commit -m "feat: pass user role and context to AI description generation"
```

---

### Task 12: Actualizar PROGRESS.md y verificación final

**Files:**
- Modify: `PROGRESS.md`

**Step 1: Run all daemon tests**

Run: `cd /opt/mimir-app/daemon && python -m pytest tests/ -v`
Expected: ALL PASS (aprox ~100 tests)

**Step 2: Run TypeScript check**

Run: `cd /opt/mimir-app && npx vue-tsc --noEmit`
Expected: 0 errors

**Step 3: Run Rust check**

Run: `cd /opt/mimir-app/src-tauri && cargo check`
Expected: OK

**Step 4: Update PROGRESS.md**

Add Fase 4 section as COMPLETADA with all tasks and test counts.

**Step 5: Commit**

```bash
git add PROGRESS.md
git commit -m "docs: mark Phase 4 (AI descriptions) as complete"
```
