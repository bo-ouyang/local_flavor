<template>
  <view class="page">
    <view class="header-wrap">
      <view class="header-top">
        <text class="brand">LocalTreasure</text>
        <view class="filter-btn">社区交流</view>
      </view>

      <view class="search-box">
        <input
          v-model="searchTerm"
          class="search-input"
          placeholder="搜索动态内容 / 商品名称 / 地点 / 标签"
          confirm-type="search"
          @confirm="loadPosts"
        />
      </view>
    </view>

    <view class="feed">
      <view class="publish-entry">
        <view class="publish-copy">
          <text class="publish-title">分享你收到的特产</text>
          <text class="publish-desc">只有完成过交换，才能发布交流动态</text>
        </view>
        <view class="publish-action" @click="goPublish">去发布</view>
      </view>

      <view class="post-card" v-for="post in posts" :key="post.id" @click="goDetail(post.id)">
        <view class="cover-wrap">
          <image :src="coverOf(post)" mode="aspectFill" class="cover" />
          <text class="tag">{{ post.item?.category || '交流' }}</text>
        </view>

        <view class="body">
          <view class="author-row">
            <view class="author-main">
              <image :src="post.user?.avatar || defaultAvatar" mode="aspectFill" class="avatar" />
              <view class="author-copy">
                <view class="author-name-row">
                  <text class="author-name">{{ post.user?.nickname || '匿名用户' }}</text>
                  <text v-if="post.author_tag" class="author-tag">{{ post.author_tag }}</text>
                </view>
                <text class="author-meta-line">
                  {{ post.item?.city || post.item?.province || '未知地区' }} · {{ formatTime(post.created_at) }}
                </text>
              </view>
            </view>
            <view
              class="like-btn"
              :class="{ liked: post.is_liked }"
              @click.stop="toggleLike(post)"
            >
              <text class="like-icon">{{ post.is_liked ? '♥' : '♡' }}</text>
              <text class="like-num">{{ post.like_count || 0 }}</text>
            </view>
          </view>

          <view class="top-row">
            <text class="title">{{ post.item?.title || '特产交流' }}</text>
            <text class="time">{{ post.comment_count || 0 }}评</text>
          </view>
          <text v-if="post.exchange_hint" class="exchange-hint">{{ post.exchange_hint }}</text>
          <text class="content">{{ post.content }}</text>
          <view class="footer">
            <text class="count">点赞 {{ post.like_count || 0 }} · 评论 {{ post.comment_count || 0 }}</text>
            <text class="hint">点击查看详情</text>
          </view>
        </view>
      </view>

      <view v-if="!loading && posts.length === 0" class="empty">
        暂无社区动态，去发布第一条吧
      </view>
    </view>

    <view class="fab" @click="goPublish">
      <text class="fab-plus">+</text>
      <text class="fab-text">发布</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { onPullDownRefresh, onShow, onTabItemTap } from '@dcloudio/uni-app'
import request from '@/utils/request'
import { ensureAuthed } from '@/utils/auth'

const posts = ref<any[]>([])
const loading = ref(false)
const searchTerm = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null

const fallbackCover = 'https://dummyimage.com/400x300/f1f5f9/94a3b8&text=Community'
const defaultAvatar = 'https://dummyimage.com/200x200/e2e8f0/94a3b8&text=User'

const coverOf = (post: any) => {
  if (Array.isArray(post?.images) && post.images.length) return post.images[0]
  if (Array.isArray(post?.item?.images) && post.item.images.length) return post.item.images[0]
  return fallbackCover
}

const loadPosts = async (isRefresh = false) => {
  loading.value = true
  try {
    const params: any = { limit: 30 }
    const q = searchTerm.value.trim()
    if (q) params.q = q
    const res: any = await request.get('/community/posts', params)
    posts.value = Array.isArray(res) ? res : []
  } catch (e) {
    console.error('load community posts failed', e)
  } finally {
    loading.value = false
    if (isRefresh) uni.stopPullDownRefresh()
  }
}

const goDetail = (id: number) => {
  uni.navigateTo({ url: `/pages/community/detail?id=${id}` })
}

const goPublish = () => {
  uni.navigateTo({ url: '/pages/community/create' })
}

const toggleLike = async (post: any) => {
  if (!ensureAuthed({ toast: '请先登录后点赞' })) return
  try {
    const res: any = await request.authPost(`/community/posts/${post.id}/like`)
    post.is_liked = !!res?.liked
    post.like_count = Number(res?.like_count || 0)
  } catch (e) {
    console.error('toggle community like failed', e)
  }
}

const formatTime = (iso?: string) => {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const now = new Date()
  if (d.toDateString() === now.toDateString()) {
    return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
  }
  return `${d.getMonth() + 1}/${d.getDate()}`
}

watch(searchTerm, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    loadPosts()
  }, 300)
})

onShow(() => {
  loadPosts()
})

onPullDownRefresh(async () => {
  await loadPosts(true)
})

onTabItemTap(() => {
  uni.pageScrollTo({ scrollTop: 0, duration: 250 })
  loadPosts(true)
})
</script>

<style>
.page {
  min-height: 100vh;
  background: #f8fafc;
  padding-bottom: 120rpx;
}

.header-wrap {
  position: sticky;
  top: 0;
  z-index: 30;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(6px);
  padding: 24rpx;
  border-bottom: 1rpx solid #e2e8f0;
}

.header-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18rpx;
}

.brand {
  font-size: 40rpx;
  font-weight: 800;
  background: linear-gradient(90deg, #ea580c, #f59e0b);
  color: transparent;
  background-clip: text;
  -webkit-background-clip: text;
}

.filter-btn {
  padding: 10rpx 18rpx;
  border-radius: 999rpx;
  background: #fff7ed;
  color: #c2410c;
  font-size: 22rpx;
  border: 1rpx solid #fed7aa;
}

.search-box {
  background: #f1f5f9;
  border-radius: 999rpx;
  padding: 0 24rpx;
}

.search-input {
  height: 72rpx;
  font-size: 26rpx;
  color: #0f172a;
}

.feed {
  padding: 16rpx 24rpx 0;
}

.publish-entry {
  margin-bottom: 18rpx;
  border-radius: 24rpx;
  padding: 20rpx;
  background: linear-gradient(135deg, #fff7ed, #ffffff);
  border: 1rpx solid #fed7aa;
  box-shadow: 0 10rpx 26rpx rgba(249, 115, 22, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}

.publish-copy {
  flex: 1;
  min-width: 0;
}

.publish-title {
  display: block;
  font-size: 28rpx;
  font-weight: 800;
  color: #9a3412;
}

.publish-desc {
  display: block;
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #c2410c;
  line-height: 1.5;
}

.publish-action {
  flex-shrink: 0;
  min-width: 144rpx;
  height: 68rpx;
  padding: 0 20rpx;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #f97316, #f59e0b);
  color: #fff;
  font-size: 24rpx;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 12rpx 24rpx rgba(249, 115, 22, 0.24);
}

.post-card {
  margin-bottom: 16rpx;
  border-radius: 22rpx;
  overflow: hidden;
  border: 1rpx solid #e2e8f0;
  background: #fff;
  box-shadow: 0 8rpx 24rpx rgba(15, 23, 42, 0.06);
}

.cover-wrap {
  position: relative;
}

.cover {
  width: 100%;
  height: 320rpx;
  background: #e2e8f0;
}

.tag {
  position: absolute;
  left: 16rpx;
  top: 16rpx;
  background: #ffedd5;
  color: #9a3412;
  border: 1rpx solid #fed7aa;
  padding: 6rpx 12rpx;
  border-radius: 10rpx;
  font-size: 20rpx;
  font-weight: 600;
}

.body {
  padding: 18rpx;
}

.author-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14rpx;
  margin-bottom: 16rpx;
}

.author-main {
  display: flex;
  align-items: center;
  gap: 12rpx;
  min-width: 0;
  flex: 1;
}

.avatar {
  width: 68rpx;
  height: 68rpx;
  border-radius: 50%;
  background: #e2e8f0;
  flex-shrink: 0;
}

.author-copy {
  min-width: 0;
  flex: 1;
}

.author-name-row {
  display: flex;
  align-items: center;
  gap: 10rpx;
  flex-wrap: wrap;
}

.author-name {
  font-size: 25rpx;
  font-weight: 700;
  color: #0f172a;
}

.author-tag {
  padding: 4rpx 12rpx;
  border-radius: 999rpx;
  background: #fff7ed;
  color: #c2410c;
  font-size: 20rpx;
  border: 1rpx solid #fed7aa;
}

.author-meta-line {
  display: block;
  margin-top: 6rpx;
  color: #64748b;
  font-size: 21rpx;
}

.like-btn {
  min-width: 104rpx;
  height: 58rpx;
  padding: 0 16rpx;
  border-radius: 999rpx;
  background: #f8fafc;
  border: 1rpx solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  flex-shrink: 0;
}

.like-btn.liked {
  background: #fff1f2;
  border-color: #fecdd3;
}

.like-icon {
  color: #e11d48;
  font-size: 24rpx;
  line-height: 1;
}

.like-num {
  color: #475569;
  font-size: 22rpx;
}

.top-row {
  display: flex;
  justify-content: space-between;
  gap: 14rpx;
  align-items: flex-start;
}

.title {
  flex: 1;
  font-size: 30rpx;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.35;
}

.time {
  color: #94a3b8;
  font-size: 22rpx;
}

.exchange-hint {
  display: block;
  margin-top: 4rpx;
  color: #ea580c;
  font-size: 22rpx;
}

.content {
  display: block;
  margin-top: 10rpx;
  color: #334155;
  font-size: 24rpx;
  line-height: 1.5;
}

.footer {
  margin-top: 12rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.count {
  color: #ea580c;
  font-size: 22rpx;
}

.hint {
  color: #94a3b8;
  font-size: 21rpx;
}

.empty {
  margin-top: 120rpx;
  text-align: center;
  color: #94a3b8;
  font-size: 24rpx;
}

.fab {
  position: fixed;
  right: 24rpx;
  bottom: calc(120rpx + env(safe-area-inset-bottom));
  min-width: 144rpx;
  height: 88rpx;
  padding: 0 24rpx;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #f97316, #f59e0b);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  box-shadow: 0 12rpx 28rpx rgba(249, 115, 22, 0.38);
  z-index: 120;
}

.fab-plus {
  color: #fff;
  font-size: 42rpx;
  line-height: 1;
}

.fab-text {
  color: #fff;
  font-size: 24rpx;
  font-weight: 700;
}
</style>
