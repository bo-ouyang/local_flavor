import { describe, expect, it, vi } from 'vitest'
import { createFavoriteControl } from './favorite-control'

describe('favorite control', () => {
  it('stays disabled when loading the current state fails', async () => {
    const setFavorite = vi.fn()
    const control = createFavoriteControl({
      fetchState: vi.fn().mockRejectedValue(new Error('offline')),
      setFavorite
    })

    await control.load(4)
    await expect(control.set(4, true)).resolves.toBeUndefined()

    expect(control.isReady.value).toBe(false)
    expect(control.isUpdating.value).toBe(false)
    expect(setFavorite).not.toHaveBeenCalled()
  })

  it('allows only one favorite update while a request is pending', async () => {
    let resolveRequest: ((value: { item_id: number; is_favorite: boolean }) => void) | undefined
    const setFavorite = vi.fn(
      () => new Promise<{ item_id: number; is_favorite: boolean }>((resolve) => {
        resolveRequest = resolve
      })
    )
    const control = createFavoriteControl({
      fetchState: vi.fn().mockResolvedValue({ item_id: 4, is_favorite: false }),
      setFavorite
    })
    await control.load(4)

    const first = control.set(4, true)
    const second = control.set(4, true)
    resolveRequest?.({ item_id: 4, is_favorite: true })
    await Promise.all([first, second])

    expect(setFavorite).toHaveBeenCalledTimes(1)
    expect(control.isFavorite.value).toBe(true)
    expect(control.isUpdating.value).toBe(false)
  })
})
