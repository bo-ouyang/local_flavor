import { beforeEach, describe, expect, it, vi } from 'vitest'

const authGet = vi.fn()
const authPost = vi.fn()
const authPut = vi.fn()
const authDelete = vi.fn()

vi.mock('@/utils/request', () => ({
  default: { authGet, authPost, authPut, authDelete }
}))

describe('favorites API', () => {
  beforeEach(() => {
    vi.resetModules()
    authGet.mockReset()
    authPost.mockReset()
    authPut.mockReset()
    authDelete.mockReset()
  })

  it('reads persisted favorites and profile stats through authenticated APIs', async () => {
    authGet
      .mockResolvedValueOnce({ items: [{ id: 4, title: 'Salted plum' }], next_skip: null, has_more: false })
      .mockResolvedValueOnce({
        completed_exchange_count: 3,
        published_item_count: 2,
        favorite_item_count: 1
      })

    const { fetchFavoriteItems, fetchProfileStats } = await import('./favorites')

    await expect(fetchFavoriteItems()).resolves.toMatchObject({ items: [{ id: 4, title: 'Salted plum' }] })
    await expect(fetchProfileStats()).resolves.toMatchObject({ completed_exchange_count: 3 })
    expect(authGet).toHaveBeenNthCalledWith(1, '/items/favorites', { skip: 0, limit: 20 })
    expect(authGet).toHaveBeenNthCalledWith(2, '/user/stats')
  })

  it('sets the desired favorite state through idempotent authenticated APIs', async () => {
    authPut.mockResolvedValue({ item_id: 4, is_favorite: true })
    authDelete.mockResolvedValue({ item_id: 4, is_favorite: false })
    const { setFavorite } = await import('./favorites')

    await expect(setFavorite(4, true)).resolves.toEqual({ item_id: 4, is_favorite: true })
    await expect(setFavorite(4, false)).resolves.toEqual({ item_id: 4, is_favorite: false })
    expect(authPut).toHaveBeenCalledWith('/items/4/favorite', undefined)
    expect(authDelete).toHaveBeenCalledWith('/items/4/favorite', undefined)
  })

  it('reads a single item favorite state through the authenticated API', async () => {
    authGet.mockResolvedValue({ item_id: 4, is_favorite: true })
    const { fetchFavoriteState } = await import('./favorites')

    await expect(fetchFavoriteState(4)).resolves.toEqual({ item_id: 4, is_favorite: true })
    expect(authGet).toHaveBeenCalledWith('/items/4/favorite')
  })
})
