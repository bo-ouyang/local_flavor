<template>
  <view class="page">
    <view class="hero">
      <view class="hero-bg"></view>
      <view class="hero-main">
        <view class="avatar-wrap">
          <image class="avatar" :src="avatarUrl" mode="aspectFill" />
          <view class="online-dot"></view>
        </view>
        <text class="name">{{ displayName }}</text>
        <text class="sub">{{ displayRegion }}</text>

        <view class="stats-grid">
          <view class="stat-item">
            <text class="stat-num">{{ profileStats.completed_exchange_count }}</text>
            <text class="stat-label">成功交换</text>
          </view>
          <view class="stat-item">
            <text class="stat-num">{{ profileStats.published_item_count }}</text>
            <text class="stat-label">我的发布</text>
          </view>
          <view class="stat-item">
            <text class="stat-num">{{ profileStats.favorite_item_count }}</text>
            <text class="stat-label">我的收藏</text>
          </view>
        </view>
      </view>
    </view>

    <view class="tabs">
      <view class="tab" :class="{ active: activeTab === 'listings' }" @click="activeTab = 'listings'">我的发布</view>
      <view class="tab" :class="{ active: activeTab === 'favorites' }" @click="activeTab = 'favorites'">我的收藏</view>
      <view class="tab" :class="{ active: activeTab === 'actions' }" @click="activeTab = 'actions'">快捷入口</view>
    </view>

    <view class="content">
      <template v-if="activeTab === 'listings'">
        <view v-if="myItems.length">
          <view class="card" v-for="item in myItems" :key="item.id" @click="goToDetail(item.id)">
            <image :src="item.images?.[0] || fallbackCover" mode="aspectFill" class="cover" />
            <view class="info">
              <text class="title">{{ item.title }}</text>
              <text class="meta">{{ item.city || item.province || '未知地区' }}</text>
            </view>
          </view>
        </view>
        <view v-else class="empty">还没有发布任何特产</view>
      </template>

      <template v-else-if="activeTab === 'favorites'">
        <view v-if="favoriteItems.length">
          <view class="card" v-for="item in favoriteItems" :key="item.id" @click="goToDetail(item.id)">
            <image :src="item.images?.[0] || fallbackCover" mode="aspectFill" class="cover" />
            <view class="info">
              <text class="title">{{ item.title }}</text>
              <text class="meta">{{ item.city || item.province || '未知地区' }}</text>
            </view>
          </view>
          <button v-if="favoriteNextSkip !== null" class="load-more" :loading="favoritesLoading" @click="loadFavorites()">加载更多</button>
        </view>
        <view v-else class="empty">还没有收藏任何特产</view>
      </template>

      <template v-else>
        <view class="entry" @click="refreshLocation">
          <text class="entry-title">{{ locating ? '定位中...' : '更新我的位置' }}</text>
          <text class="entry-arrow">›</text>
        </view>
        <view class="entry" @click="goToPublish">
          <text class="entry-title">发布特产</text>
          <text class="entry-arrow">›</text>
        </view>
        <view class="entry" @click="goToMessages">
          <text class="entry-title">我的消息</text>
          <text class="entry-arrow">›</text>
        </view>
        <view class="entry" @click="goToExchange">
          <text class="entry-title">我的交换</text>
          <text class="entry-arrow">›</text>
        </view>
        <button v-if="isAuthed" class="logout" @click="logout">退出登录</button>
        <button v-else class="login" @click="goLogin()">去登录</button>
      </template>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onReachBottom, onShow } from '@dcloudio/uni-app'
import { useUserStore } from '@/stores/user'
import request from '@/utils/request'
import { ensureAuthed, goLogin } from '@/utils/auth'
import { fetchFavoriteItems, fetchProfileStats, type ProfileStats } from '@/utils/favorites'

const userStore = useUserStore()
const myItems = ref<any[]>([])
const favoriteItems = ref<any[]>([])
const favoriteNextSkip = ref<number | null>(0)
const favoritesLoading = ref(false)
const activeTab = ref<'listings' | 'favorites' | 'actions'>('listings')
const locating = ref(false)
const profileStats = ref<ProfileStats>({
  completed_exchange_count: 0,
  published_item_count: 0,
  favorite_item_count: 0
})

const fallbackCover = 'https://dummyimage.com/400x300/f1f5f9/94a3b8&text=Local+Treasure'
const defaultAvatar = 'https://dummyimage.com/200x200/e2e8f0/94a3b8&text=Avatar'

const isAuthed = computed(() => !!userStore.token)
const displayName = computed(() => {
  if (!isAuthed.value) return '游客'
  return userStore.userInfo.nickname || `用户${userStore.userInfo.id}`
})
const displayRegion = computed(() => {
  if (!isAuthed.value) return '登录后可发布和交换特产'
  return userStore.userInfo.region || `${userStore.userInfo.city || ''} ${userStore.userInfo.province || ''}`.trim() || '暂未设置地区'
})
const avatarUrl = computed(() => userStore.userInfo.avatar || defaultAvatar)
const goToPublish = () => {
  if (!ensureAuthed({ toast: '请先登录后发布', redirect: '/pages/publish/publish' })) return
  uni.switchTab({ url: '/pages/publish/publish' })
}

const goToDetail = (id: number) => {
  uni.navigateTo({ url: `/pages/detail/detail?id=${id}` })
}

const goToMessages = () => {
  if (!ensureAuthed({ toast: '请先登录后查看消息' })) return
  uni.navigateTo({ url: '/pages/chat/list' })
}

const goToExchange = () => {
  if (!ensureAuthed({ toast: '请先登录后查看交换记录' })) return
  uni.navigateTo({ url: '/pages/exchange/list' })
}

const refreshLocation = async () => {
  if (!ensureAuthed({ toast: '请先登录后更新位置' })) return
  if (locating.value) return
  locating.value = true
  try {
    const locRes: any = await uni.getLocation({ type: 'gcj02' })
    const latitude = Number(locRes?.latitude)
    const longitude = Number(locRes?.longitude)
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
      throw new Error('invalid location')
    }
    const updated: any = await userStore.updateRegionByCoords({ latitude, longitude })
    const city = updated?.city || userStore.userInfo.city || ''
    const province = updated?.province || userStore.userInfo.province || ''
    uni.showToast({ title: city && province ? `已更新为 ${city}, ${province}` : '位置已更新', icon: 'none' })
  } catch (e: any) {
    const detail = e?.errors?.detail || e?.message || '更新位置失败'
    uni.showToast({ title: String(detail), icon: 'none' })
  } finally {
    locating.value = false
  }
}

const logout = async () => {
  await userStore.logout()
  uni.showToast({ title: '已退出登录', icon: 'none' })
}

const loadMyItems = async () => {
  if (!isAuthed.value || !userStore.userInfo.id) {
    myItems.value = []
    return
  }
  try {
    const res: any = await request.get('/items/', { publisher_id: userStore.userInfo.id, limit: 100 })
    myItems.value = Array.isArray(res) ? res : []
  } catch (e) {
    console.error('load my items failed', e)
  }
}

const loadFavorites = async (reset = false) => {
  if (!isAuthed.value) {
    favoriteItems.value = []
    favoriteNextSkip.value = null
    return
  }
  if (favoritesLoading.value || (!reset && favoriteNextSkip.value === null)) return
  const skip = reset ? 0 : favoriteNextSkip.value || 0
  if (reset) {
    favoriteItems.value = []
    favoriteNextSkip.value = 0
  }
  favoritesLoading.value = true
  try {
    const page = await fetchFavoriteItems(skip)
    favoriteItems.value = reset ? page.items : [...favoriteItems.value, ...page.items]
    favoriteNextSkip.value = page.next_skip
  } catch (e) {
    console.error('load favorites failed', e)
  } finally {
    favoritesLoading.value = false
  }
}

const loadProfileStats = async () => {
  if (!isAuthed.value) {
    profileStats.value = {
      completed_exchange_count: 0,
      published_item_count: 0,
      favorite_item_count: 0
    }
    return
  }
  try {
    profileStats.value = await fetchProfileStats()
  } catch (e) {
    console.error('load profile stats failed', e)
  }
}

onShow(async () => {
  if (isAuthed.value && !userStore.userInfo.id) {
    try {
      await userStore.fetchUserInfo()
    } catch (e) {
      console.error('fetch profile failed', e)
    }
  }
  await Promise.all([loadMyItems(), loadFavorites(true), loadProfileStats()])
})

onReachBottom(() => {
  if (activeTab.value === 'favorites') loadFavorites()
})
</script>

<style>
.page {
  min-height: 100vh;
  background: #f8fafc;
}

.hero {
  position: relative;
  margin-bottom: 14rpx;
}

.hero-bg {
  height: 180rpx;
  background: linear-gradient(90deg, #fb923c, #f59e0b);
}

.hero-main {
  margin: -66rpx 24rpx 0;
  border-radius: 24rpx;
  background: #fff;
  border: 1rpx solid #e2e8f0;
  padding: 22rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.avatar-wrap {
  position: relative;
}

.avatar {
  width: 132rpx;
  height: 132rpx;
  border-radius: 50%;
  border: 4rpx solid #fff;
  background: #e2e8f0;
}

.online-dot {
  position: absolute;
  right: 2rpx;
  bottom: 4rpx;
  width: 20rpx;
  height: 20rpx;
  border-radius: 50%;
  background: #22c55e;
  border: 2rpx solid #fff;
}

.name {
  margin-top: 10rpx;
  font-size: 34rpx;
  color: #0f172a;
  font-weight: 800;
}

.sub {
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #64748b;
}

.stats-grid {
  margin-top: 18rpx;
  width: 100%;
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 10rpx;
}

.stat-item {
  background: #f8fafc;
  border: 1rpx solid #e2e8f0;
  border-radius: 14rpx;
  padding: 14rpx 10rpx;
  text-align: center;
}

.stat-num {
  display: block;
  color: #0f172a;
  font-size: 30rpx;
  font-weight: 700;
}

.stat-label {
  display: block;
  margin-top: 4rpx;
  color: #64748b;
  font-size: 20rpx;
}

.tabs {
  margin: 0 24rpx;
  background: #e2e8f0;
  border-radius: 14rpx;
  padding: 6rpx;
  display: flex;
}

.tab {
  flex: 1;
  text-align: center;
  font-size: 23rpx;
  color: #475569;
  padding: 14rpx 0;
  border-radius: 10rpx;
}

.tab.active {
  background: #fff;
  color: #0f172a;
  font-weight: 700;
}

.content {
  padding: 18rpx 24rpx 30rpx;
}

.card {
  background: #fff;
  border: 1rpx solid #e2e8f0;
  border-radius: 18rpx;
  overflow: hidden;
  margin-bottom: 14rpx;
}

.cover {
  width: 100%;
  height: 280rpx;
  background: #e2e8f0;
}

.info {
  padding: 14rpx;
}

.title {
  display: block;
  font-size: 28rpx;
  color: #0f172a;
  font-weight: 700;
}

.meta {
  display: block;
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #64748b;
}

.empty {
  text-align: center;
  color: #94a3b8;
  margin-top: 90rpx;
  font-size: 24rpx;
}

.entry {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border: 1rpx solid #e2e8f0;
  border-radius: 14rpx;
  padding: 20rpx;
  margin-bottom: 12rpx;
}

.entry-title {
  font-size: 26rpx;
  color: #0f172a;
  font-weight: 600;
}

.entry-arrow {
  color: #94a3b8;
  font-size: 34rpx;
}

.logout,
.login {
  margin-top: 8rpx;
  border-radius: 14rpx;
  height: 84rpx;
  line-height: 84rpx;
  font-size: 28rpx;
}

.logout {
  background: #fff;
  color: #334155;
  border: 1rpx solid #e2e8f0;
}

.login {
  background: #0f172a;
  color: #fff;
  border: none;
}
</style>
