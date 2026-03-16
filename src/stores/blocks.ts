import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { ActivityBlock, Signal } from '../lib/types';
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

  const confirmedHoursToday = computed(() =>
    blocks.value
      .filter(b => b.status === 'confirmed' || b.status === 'synced')
      .reduce((sum, b) => sum + b.duration_minutes / 60, 0)
  );

  const unconfirmedHoursToday = computed(() =>
    blocks.value
      .filter(b => b.status === 'auto' || b.status === 'closed')
      .reduce((sum, b) => sum + b.duration_minutes / 60, 0)
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
    if (confirmedIds.length === 0) return;
    const result = await api.syncBlocks(confirmedIds) as { synced: number; errors: Array<{ block_id: number; error: string }> };
    await fetchBlocks();
    return result;
  }

  async function retrySync(blockId: number) {
    try {
      await api.retrySync(blockId);
      const block = blocks.value.find(b => b.id === blockId);
      if (block) {
        block.status = 'synced';
        block.sync_error = null;
      }
    } catch (e) {
      // Refrescar para obtener el estado actualizado
      await fetchBlocks();
      throw e;
    }
  }

  const confirmedBlocks = computed(() =>
    blocks.value.filter(b => b.status === 'confirmed')
  );

  const errorBlocks = computed(() =>
    blocks.value.filter(b => b.status === 'error')
  );

  const closedBlocks = computed(() =>
    blocks.value.filter(b => b.status === 'closed')
  );

  // --- Signals ---

  const signals = ref<Signal[]>([]);
  const signalsLoading = ref(false);

  async function fetchSignals(date?: string, blockId?: number) {
    signalsLoading.value = true;
    try {
      signals.value = await api.getSignals(date || selectedDate.value, blockId) as Signal[];
    } catch { signals.value = []; }
    finally { signalsLoading.value = false; }
  }

  async function splitBlock(blockId: number, signalId: number) {
    await api.splitBlock(blockId, signalId);
    await fetchBlocks();
  }

  async function mergeBlocks(blockIds: number[]) {
    await api.mergeBlocks(blockIds);
    await fetchBlocks();
  }

  return {
    blocks,
    selectedDate,
    loading,
    error,
    pendingBlocks,
    confirmedBlocks,
    errorBlocks,
    syncedBlocks,
    totalHoursToday,
    confirmedHoursToday,
    unconfirmedHoursToday,
    fetchBlocks,
    confirmBlock,
    updateBlock,
    deleteBlock,
    syncToOdoo,
    retrySync,
    closedBlocks,
    signals,
    signalsLoading,
    fetchSignals,
    splitBlock,
    mergeBlocks,
  };
});
