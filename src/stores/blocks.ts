import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { ActivityBlock } from '../lib/types';
import { api } from '../lib/api';

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
      const d = date ?? selectedDate.value;
      blocks.value = await api.getBlocks(d) as ActivityBlock[];
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    } finally {
      loading.value = false;
    }
  }

  async function confirmBlock(blockId: number) {
    await api.confirmBlock(blockId);
    const block = blocks.value.find(b => b.id === blockId);
    if (block) block.status = 'confirmed';
  }

  async function updateBlock(blockId: number, updates: Partial<ActivityBlock>) {
    await api.updateBlock(blockId, updates);
    const block = blocks.value.find(b => b.id === blockId);
    if (block) Object.assign(block, updates);
  }

  async function deleteBlock(blockId: number) {
    await api.deleteBlock(blockId);
    blocks.value = blocks.value.filter(b => b.id !== blockId);
  }

  async function syncToOdoo() {
    const confirmedIds = blocks.value
      .filter(b => b.status === 'confirmed')
      .map(b => b.id);
    await api.syncBlocks(confirmedIds);
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
    deleteBlock,
    syncToOdoo,
  };
});
