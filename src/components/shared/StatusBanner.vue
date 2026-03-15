<script setup lang="ts">
withDefaults(defineProps<{
  type: 'success' | 'error' | 'warning' | 'info';
  dismissible?: boolean;
}>(), {
  dismissible: false,
});

const emit = defineEmits<{ dismiss: [] }>();
</script>

<template>
  <div class="banner" :class="type">
    <span class="banner-text"><slot /></span>
    <button v-if="dismissible" class="banner-close" @click="emit('dismiss')">&times;</button>
  </div>
</template>

<style scoped>
.banner {
  padding: 10px 14px;
  border-radius: 4px;
  font-size: 13px;
  margin-bottom: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.banner.error { background: rgba(241, 76, 76, 0.1); border: 1px solid var(--error); color: var(--error); }
.banner.success { background: rgba(78, 201, 176, 0.1); border: 1px solid var(--success); color: var(--success); }
.banner.warning { background: rgba(220, 220, 170, 0.1); border: 1px solid var(--warning); color: var(--warning); }
.banner.info { background: rgba(86, 156, 214, 0.1); border: 1px solid var(--text-secondary); color: var(--text-secondary); }
.banner-text { flex: 1; }
.banner-close {
  background: none; border: none; color: inherit; font-size: 18px;
  cursor: pointer; padding: 0 4px; opacity: 0.7;
}
.banner-close:hover { opacity: 1; }
</style>
