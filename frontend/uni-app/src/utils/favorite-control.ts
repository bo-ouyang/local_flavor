import { computed, ref } from 'vue'
import type { FavoriteState } from './favorites'

type FavoriteApi = {
  fetchState: (itemId: number) => Promise<FavoriteState>
  setFavorite: (itemId: number, isFavorite: boolean) => Promise<FavoriteState>
}

export const createFavoriteControl = (api: FavoriteApi) => {
  const isFavorite = ref(false)
  const isReady = ref(false)
  const isUpdating = ref(false)
  let loadVersion = 0

  const canUpdate = computed(() => isReady.value && !isUpdating.value)

  const reset = () => {
    loadVersion += 1
    isFavorite.value = false
    isReady.value = false
    isUpdating.value = false
  }

  const load = async (itemId: number) => {
    const version = ++loadVersion
    isReady.value = false
    try {
      const state = await api.fetchState(itemId)
      if (version !== loadVersion) return false
      isFavorite.value = state.is_favorite
      isReady.value = true
      return true
    } catch {
      if (version === loadVersion) isFavorite.value = false
      return false
    }
  }

  const set = async (itemId: number, desiredState: boolean) => {
    if (!canUpdate.value) return undefined
    isUpdating.value = true
    try {
      const state = await api.setFavorite(itemId, desiredState)
      isFavorite.value = state.is_favorite
      return state
    } finally {
      isUpdating.value = false
    }
  }

  return { isFavorite, isReady, isUpdating, canUpdate, reset, load, set }
}
