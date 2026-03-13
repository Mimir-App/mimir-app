import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { ActivityBlock } from '../lib/types';

export const useBlocksStore = defineStore('blocks', () => {
  const blocks = ref<ActivityBlock[]>([]);
  const selectedDate = ref(new Date().toISOString().slice(0, 10));
  const loading = ref(false);
  const error = ref<string | null>(null);

  const pendingBlocks = computed(() =>
    blocks.value.filter(b => b.status === 'auto' || b.status === 'confirmed')
  );

  const syncedBlocks = computed(() =>
    blocks.value.filter(b => b.status === 'synced')
  );

  const totalHoursToday = computed(() =>
    blocks.value.reduce((sum, b) => sum + b.duration_minutes / 60, 0)
  );

  async function fetchBlocks(date?: string) {
    loading.value = true;
    error.value = null;
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      const d = date ?? selectedDate.value;
      blocks.value = await invoke<ActivityBlock[]>('get_blocks', { date: d });
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    } finally {
      loading.value = false;
    }
  }

  async function confirmBlock(blockId: number) {
    const { invoke } = await import('@tauri-apps/api/core');
    await invoke('confirm_block', { blockId });
    const block = blocks.value.find(b => b.id === blockId);
    if (block) block.status = 'confirmed';
  }

  async function updateBlock(blockId: number, updates: Partial<ActivityBlock>) {
    const { invoke } = await import('@tauri-apps/api/core');
    await invoke('update_block', { blockId, updates });
    const block = blocks.value.find(b => b.id === blockId);
    if (block) Object.assign(block, updates);
  }

  async function syncToOdoo() {
    const { invoke } = await import('@tauri-apps/api/core');
    const confirmedIds = blocks.value
      .filter(b => b.status === 'confirmed')
      .map(b => b.id);
    await invoke('sync_blocks_to_odoo', { blockIds: confirmedIds });
    await fetchBlocks();
  }

  return {
    blocks,
    selectedDate,
    loading,
    error,
    pendingBlocks,
    syncedBlocks,
    totalHoursToday,
    fetchBlocks,
    confirmBlock,
    updateBlock,
    syncToOdoo,
  };
});
