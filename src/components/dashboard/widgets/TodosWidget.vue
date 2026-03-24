<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { api } from '../../../lib/api';
import type { GitLabTodo } from '../../../lib/types';
import EmptyState from '../../shared/EmptyState.vue';

const props = defineProps<{ config: Record<string, any> }>();

const todos = ref<GitLabTodo[]>([]);
const loading = ref(false);
const error = ref(false);

const count = computed(() => props.config.count ?? 10);
const visibleTodos = computed(() => todos.value.slice(0, count.value));

async function fetchTodos() {
  loading.value = true;
  try {
    todos.value = await api.getGitlabTodos();
  } catch { todos.value = []; error.value = true; }
  finally { loading.value = false; }
}

onMounted(() => fetchTodos());
</script>

<template>
  <h3 class="widget-title">Todos GitLab</h3>
  <p v-if="error" class="widget-error">Error al cargar</p>
  <div class="todos-list">
    <div v-for="todo in visibleTodos" :key="todo.id" class="todo-row">
      <span class="todo-action">{{ todo.action_name }}</span>
      <span class="todo-project">{{ todo.project.path_with_namespace }}</span>
      <span class="todo-title">{{ todo.target.title }}</span>
    </div>
    <EmptyState v-if="visibleTodos.length === 0 && !loading" text="Sin TODOs pendientes" />
  </div>
</template>

<style scoped>
.widget-title { font-size: var(--text-xs); font-weight: 600; color: var(--text-secondary); margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
.todos-list { display: flex; flex-direction: column; gap: 6px; }
.todo-row { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 4px; font-size: 13px; }
.todo-row:hover { background: var(--bg-hover); }
.todo-action { min-width: 80px; font-size: 11px; font-weight: 600; color: var(--accent); text-transform: uppercase; }
.todo-project { color: var(--text-secondary); font-size: 12px; min-width: 150px; }
.todo-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.widget-error { font-size: 11px; color: var(--text-secondary); font-style: italic; text-align: center; margin: 8px 0; }
</style>
