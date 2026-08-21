import request from '@/utils/request'

export type FavoriteState = {
  item_id: number
  is_favorite: boolean
}

export type FavoritePage<T = any> = {
  items: T[]
  next_skip: number | null
  has_more: boolean
}

export type ProfileStats = {
  completed_exchange_count: number
  published_item_count: number
  favorite_item_count: number
}

export const fetchFavoriteItems = (skip = 0, limit = 20) =>
  request.authGet<FavoritePage>('/items/favorites', { skip, limit })

export const fetchFavoriteState = (itemId: number) =>
  request.authGet<FavoriteState>(`/items/${itemId}/favorite`)

export const setFavorite = (itemId: number, isFavorite: boolean) =>
  isFavorite
    ? request.authPut<FavoriteState>(`/items/${itemId}/favorite`, undefined)
    : request.authDelete<FavoriteState>(`/items/${itemId}/favorite`, undefined)

export const fetchProfileStats = () => request.authGet<ProfileStats>('/user/stats')
