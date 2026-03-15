import { ref, computed, provide, inject, nextTick, type InjectionKey, type Ref, reactive } from 'vue';

interface CollapseContext {
  signal: Ref<boolean | null>;
  register: (id: string, collapsed: Ref<boolean>) => void;
  unregister: (id: string) => void;
}

const COLLAPSE_KEY: InjectionKey<CollapseContext> = Symbol('collapseAll');

/**
 * Usar en la vista padre para controlar colapso global.
 * Detecta el estado real de todos los grupos registrados.
 */
export function provideCollapseAll() {
  const signal = ref<boolean | null>(null);
  const groupStates = reactive<Map<string, Ref<boolean>>>(new Map());

  function register(id: string, collapsed: Ref<boolean>) {
    groupStates.set(id, collapsed);
  }

  function unregister(id: string) {
    groupStates.delete(id);
  }

  const allCollapsed = computed(() => {
    if (groupStates.size === 0) return false;
    for (const collapsed of groupStates.values()) {
      if (!collapsed.value) return false;
    }
    return true;
  });

  const allExpanded = computed(() => {
    if (groupStates.size === 0) return true;
    for (const collapsed of groupStates.values()) {
      if (collapsed.value) return false;
    }
    return true;
  });

  provide(COLLAPSE_KEY, { signal, register, unregister });

  async function toggle() {
    // Si todos estan expandidos -> colapsar. Si no -> expandir.
    const shouldCollapse = allExpanded.value;
    signal.value = shouldCollapse;
    await nextTick();
    signal.value = null;
  }

  return { allCollapsed, allExpanded, toggle };
}

/**
 * Usar en CollapsibleGroup para escuchar el signal y reportar estado.
 */
export function injectCollapseContext(): CollapseContext | undefined {
  return inject(COLLAPSE_KEY, undefined);
}
