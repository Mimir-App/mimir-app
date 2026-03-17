# Refactor Settings + MR Popup + Dashboard + Notifications — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan.

**Goal:** Refactor SettingsView into tab components, add MR detail popup with conflicts/filters, make dashboard fully configurable with widget gallery, and implement notification system (in-app + desktop + tray).

**Architecture:** 4 independent chunks. Chunk 1 refactors Settings (prerequisite for NotificationsTab). Chunk 2 adds MR features + migrates item_preferences. Chunk 3 rebuilds dashboard with widget system. Chunk 4 adds notifications backend + frontend.

**Tech Stack:** Vue 3 + TypeScript, Python FastAPI, Rust Tauri 2, SQLite, tauri-plugin-notification.

---

## Chunk 1: Settings Refactor

### Task 1: Create base settings components
- Create: `src/components/settings/SettingGroup.vue`
- Create: `src/components/settings/SettingRow.vue`
- Create: `src/components/settings/CredentialField.vue`

### Task 2: Extract 7 tab components from SettingsView
- Create: `src/components/settings/GeneralTab.vue` (from lines 252-327)
- Create: `src/components/settings/CaptureTab.vue` (from lines 330-375)
- Create: `src/components/settings/OdooTab.vue` (from lines 378-462)
- Create: `src/components/settings/GitLabTab.vue` (from lines 465-577)
- Create: `src/components/settings/AITab.vue` (from lines 578-629)
- Create: `src/components/settings/GoogleTab.vue` (from lines 630-692)
- Create: `src/components/settings/ServicesTab.vue` (from lines 693-1150)
- Modify: `src/views/SettingsView.vue` → shell with dynamic component

Verify: `npx vue-tsc --noEmit`

---

## Chunk 2: MR Features + item_preferences migration

### Task 3: Replace issue_preferences with item_preferences in DB
- Modify: `daemon/mimir_daemon/db.py` — drop issue_preferences, create item_preferences table, update CRUD methods
- Modify: `daemon/mimir_daemon/server.py` — replace issue preference endpoints with generic `/items/{type}/{id}/preferences`
- Tests: `daemon/tests/test_server.py`

### Task 4: GitLab source MR methods + todos + user
- Modify: `daemon/mimir_daemon/sources/gitlab.py` — add search_merge_requests, get_mr_notes, get_mr_conflicts, get_merge_requests_by_ids, get_todos, get_current_user
- Modify: `daemon/mimir_daemon/server.py` — add MR endpoints + todos + user
- Tests: `daemon/tests/test_gitlab_source.py`

### Task 5: Tauri commands + API + types migration
- Modify: `src-tauri/src/commands/daemon.rs` — new MR commands, replace issue preference commands
- Modify: `src-tauri/src/lib.rs` — register new commands
- Modify: `src/lib/types.ts` — ItemPreference replaces IssuePreference, add MR conflict types
- Modify: `src/lib/api.ts` — new methods, replace issue preference methods
- Modify: `src/stores/issues.ts` — migrate to item_preferences API
- Modify: `src/components/issues/IssueDetailModal.vue` — use new API

Verify: `cargo check`, `npx vue-tsc --noEmit`

### Task 6: MR store + MRsView + MRDetailModal
- Modify: `src/stores/merge_requests.ts` — add preferences, followed, search, filters
- Create: `src/views/MRsView.vue` — full view with search, filters, table
- Create: `src/components/merge_requests/MRDetailModal.vue` — detail popup with conflicts
- Modify: `src/components/merge_requests/MRTable.vue` — add select emit, followed indicator

Verify: `npx vue-tsc --noEmit`, `python3 -m pytest tests/ -v`

---

## Chunk 3: Dashboard Configurable

### Task 7: Widget registry + DashboardGrid refactor
- Create: `src/lib/widget-registry.ts`
- Modify: `src/components/shared/DashboardGrid.vue` — accept new DashboardWidget model
- Modify: `src/lib/types.ts` — add DashboardWidget interface
- Modify: `src-tauri/src/commands/config.rs` — add dashboard_widgets to AppConfig

### Task 8: Extract existing widgets to components
- Create: `src/components/dashboard/widgets/JornadaWidget.vue`
- Create: `src/components/dashboard/widgets/ServiciosWidget.vue`
- Create: `src/components/dashboard/widgets/HorasHoyWidget.vue`
- Create: `src/components/dashboard/widgets/ProgresoWidget.vue`
- Create: `src/components/dashboard/widgets/TopIssuesWidget.vue`

### Task 9: New widgets
- Create: `src/components/dashboard/widgets/MRsPendientesWidget.vue`
- Create: `src/components/dashboard/widgets/IssuesProyectoWidget.vue`
- Create: `src/components/dashboard/widgets/HorasSemanaWidget.vue`
- Create: `src/components/dashboard/widgets/CalendarioWidget.vue`
- Create: `src/components/dashboard/widgets/TodosWidget.vue`

### Task 10: Widget config + gallery UI
- Create: `src/components/dashboard/WidgetConfigModal.vue`
- Create: `src/components/dashboard/WidgetGallery.vue`
- Modify: `src/views/DashboardView.vue` — use registry, add/remove widgets, config modal

Verify: `npx vue-tsc --noEmit`

---

## Chunk 4: Notifications

### Task 11: Notification backend
- Create: `daemon/mimir_daemon/notifications.py` — NotificationService with async loop
- Modify: `daemon/mimir_daemon/db.py` — notifications table + CRUD
- Modify: `daemon/mimir_daemon/server.py` — notification endpoints + startup task
- Tests: `daemon/tests/test_notifications.py`

### Task 12: Notification frontend
- Create: `src/components/shared/NotificationBell.vue`
- Create: `src/components/settings/NotificationsTab.vue`
- Modify: `src/components/layout/AppHeader.vue` — add NotificationBell
- Modify: `src/views/SettingsView.vue` — add Notifications tab
- Modify: `src/lib/types.ts` — notification config fields in AppConfig
- Modify: `src/lib/api.ts` — notification API methods
- Tauri commands for notifications

### Task 13: Desktop notifications + tray badge
- Modify: `src-tauri/Cargo.toml` — add tauri-plugin-notification
- Modify: `src-tauri/src/lib.rs` — register notification plugin
- Frontend logic: send desktop notification when new notification arrives and app not focused

Verify: all tests + type check + cargo check
