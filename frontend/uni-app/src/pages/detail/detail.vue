<template>
  <view class="page" v-if="item">
    <view class="hero">
      <swiper class="hero-swiper" indicator-dots>
        <swiper-item v-for="img in item.images" :key="img">
          <image :src="img" mode="aspectFill" class="hero-image" />
        </swiper-item>
      </swiper>
      <view class="hero-mask"></view>

      <view class="hero-actions">
        <view class="icon-btn" @click="goBack">‹</view>
        <view class="right-actions">
          <view class="icon-btn" :class="{ fav: favoriteControl.isFavorite.value, disabled: !favoriteControl.canUpdate.value }" @click="toggleFavorite">♥</view>
        </view>
      </view>
    </view>

    <view class="content-card">
      <view class="title-row">
        <view class="title-side">
          <text class="category">{{ categoryMap[item.category] || item.category }}</text>
          <text class="title">{{ item.title }}</text>
        </view>
      </view>

      <view class="meta-line">
        <text>{{ item.city || item.province || '未知地区' }}</text>
        <text class="dot">·</text>
        <text>{{ seasonMap[item.season] || item.season || '四季' }}</text>
      </view>

      <text class="desc">{{ item.description || '暂无描述' }}</text>

      <view class="specs">
        <text class="spec">保质期：{{ shelfLifeMap[item.shelf_life] || item.shelf_life || '-' }}</text>
        <text class="spec">便携度：{{ portabilityMap[item.portability] || item.portability || '-' }}</text>
      </view>

      <view class="flavors" v-if="item.flavor_tags && item.flavor_tags.length">
        <view
          class="flavor"
          :class="{ voted: tag.is_voted }"
          v-for="tag in item.flavor_tags"
          :key="tag.tag_name"
          @click="vote(tag.tag_name)"
        >
          {{ tag.tag_name }} ({{ tag.vote_count }})
        </view>
      </view>

      <view class="owner-card" v-if="item.publisher">
        <image :src="item.publisher.avatar || defaultAvatar" mode="aspectFill" class="owner-avatar" />
        <view class="owner-info">
          <text class="owner-name">{{ item.publisher.nickname || ('用户' + item.publisher.id) }}</text>
          <text class="owner-tip">想了解详情可直接沟通</text>
        </view>
        <view class="owner-btn swap" v-if="canExchange" @click="startExchange">交换</view>
        <view class="owner-btn chat" @click="startChat">私聊</view>
      </view>
    </view>

    <view class="comment-card">
      <text class="comment-title">评论区</text>

      <view class="comment-list">
        <view class="comment-item" v-for="comment in flatComments" :key="comment.id" :style="{ marginLeft: `${comment.level * 20}rpx` }">
          <view class="comment-main" @click="startReply(comment)">
            <text class="comment-user">{{ comment.user?.nickname || ('用户' + comment.user_id) }}</text>
            <text class="comment-content">{{ comment.content }}</text>
            <text class="comment-meta">{{ formatDate(comment.created_at) }} · Lv{{ comment.level }} · 点此回复</text>
          </view>
        </view>
        <view v-if="flatComments.length === 0" class="empty">暂无评论</view>
      </view>
    </view>

    <view class="input-wrap">
      <template v-if="isLocal">
        <view class="reply-banner" v-if="replyTo">
          <text>回复 {{ replyTo.user?.nickname || ('用户' + replyTo.user_id) }}</text>
          <text class="cancel" @click="cancelReply">取消</text>
        </view>
        <view class="input-row">
          <input v-model="commentText" :placeholder="replyPlaceholder" class="comment-input" />
          <button size="mini" class="send" @click="submitComment">发送</button>
        </view>
      </template>
      <template v-else>
        <view class="not-local">仅限本地用户参与评论</view>
      </template>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import request from '@/utils/request'
import { useUserStore } from '@/stores/user'
import { ensureAuthed } from '@/utils/auth'
import { createFavoriteControl } from '@/utils/favorite-control'
import { fetchFavoriteState, setFavorite } from '@/utils/favorites'

const userStore = useUserStore()
const item = ref<any>(null)
const commentsTree = ref<any[]>([])
const commentText = ref('')
const replyTo = ref<any>(null)
const myItems = ref<any[]>([])
const favoriteControl = createFavoriteControl({
  fetchState: fetchFavoriteState,
  setFavorite
})

const defaultAvatar = 'https://dummyimage.com/200x200/e2e8f0/94a3b8&text=User'

const categoryMap = ref<Record<string, string>>({})
const shelfLifeMap = ref<Record<string, string>>({})
const portabilityMap = ref<Record<string, string>>({})
const seasonMap = ref<Record<string, string>>({
  Spring: '春',
  Summer: '夏',
  Autumn: '秋',
  Winter: '冬',
  AllYear: '四季',
})

const flatComments = computed(() => {
  const out: any[] = []
  const walk = (nodes: any[], level = 0) => {
    for (const node of nodes || []) {
      out.push({ ...node, level })
      if (node.replies?.length) walk(node.replies, level + 1)
    }
  }
  walk(commentsTree.value, 0)
  return out
})

const isLocal = computed(() => {
  if (!item.value || !userStore.userInfo.region_code) return false
  return item.value.region_code === userStore.userInfo.region_code
})

const canExchange = computed(() => {
  return !!item.value && !!userStore.userInfo.id && item.value.user_id !== userStore.userInfo.id
})

const replyPlaceholder = computed(() => {
  return replyTo.value ? `回复 ${replyTo.value.user?.nickname || '用户'}...` : '分享你的本地见解...'
})

const goBack = () => {
  const pages = getCurrentPages()
  if (pages.length > 1) {
    uni.navigateBack()
    return
  }
  uni.switchTab({ url: '/pages/index/index' })
}

const updateFavoriteState = async (itemId: number) => {
  if (!userStore.token) {
    favoriteControl.reset()
    return
  }
  const loaded = await favoriteControl.load(itemId)
  if (!loaded) console.error('load favorite state failed')
}

const toggleFavorite = async () => {
  if (!item.value?.id) return
  if (!ensureAuthed({ toast: '请先登录后收藏' })) return
  if (!favoriteControl.canUpdate.value) return
  try {
    const result = await favoriteControl.set(item.value.id, !favoriteControl.isFavorite.value)
    if (!result) return
    uni.showToast({ title: result.is_favorite ? '已收藏' : '已取消收藏', icon: 'none' })
  } catch (e) {
    console.error('toggle favorite failed', e)
  }
}

const loadOptions = async () => {
  try {
    const res: any = await request.get('/options/')
    ;(res || []).forEach((opt: any) => {
      if (opt.type === 'Category') categoryMap.value[opt.value] = opt.label
      if (opt.type === 'ShelfLife') shelfLifeMap.value[opt.value] = opt.label
      if (opt.type === 'Portability') portabilityMap.value[opt.value] = opt.label
      if (opt.type === 'Season') seasonMap.value[opt.value] = opt.label
    })
  } catch (e) {
    console.error('load options failed', e)
  }
}

const loadDetail = async (id: string) => {
  const res: any = await request.get(`/items/${id}`)
  item.value = res
  if (res?.id) await updateFavoriteState(res.id)
}

const loadComments = async (id: string) => {
  try {
    const res: any = await request.get(`/comments/${id}`, { root_limit: 100 })
    commentsTree.value = Array.isArray(res) ? res : []
  } catch (e) {
    console.error('load comments failed', e)
  }
}

const loadMyItems = async () => {
  if (!userStore.userInfo.id) return
  try {
    const res: any = await request.get('/items/', { publisher_id: userStore.userInfo.id, limit: 50 })
    myItems.value = Array.isArray(res) ? res : []
  } catch (e) {
    console.error('load my items failed', e)
  }
}

const vote = async (tagName: string) => {
  if (!ensureAuthed({ toast: '请先登录后投票' })) return
  try {
    const res: any = await request.authPost(`/items/${item.value.id}/flavor`, { tag_name: tagName })
    const msgMap: Record<string, string> = {
      voted: '已投票',
      switched: '已切换投票',
      unvoted: '已取消投票'
    }
    uni.showToast({ title: msgMap[res.status] || '操作成功', icon: 'none' })
    await loadDetail(String(item.value.id))
  } catch (e) {
    console.error('vote failed', e)
  }
}

const startChat = () => {
  if (!item.value?.publisher) return
  if (!ensureAuthed({ toast: '请先登录后发起私聊' })) return

  request
    .authPost('/chat/conversations/ensure', {
      target_id: item.value.publisher.id,
      item_id: item.value.id
    })
    .then((conv: any) => {
      const nickname = encodeURIComponent(item.value.publisher.nickname || ('用户' + item.value.publisher.id))
      uni.navigateTo({
        url: `/pages/chat/chat?conversationId=${conv.conversation_id}&nickname=${nickname}`
      })
    })
    .catch((e) => {
      console.error('ensure conversation failed', e)
    })
}

const submitExchange = async (offeredItemId?: number | null) => {
  if (!item.value) return
  if (!ensureAuthed({ toast: '请先登录后发起交换' })) return
  try {
    await request.authPost('/exchange/requests', {
      requested_item_id: item.value.id,
      offered_item_id: offeredItemId || null,
      message: '你好，想和你交换特产'
    })
    uni.showToast({ title: '交换请求已发送', icon: 'success' })
  } catch (e) {
    console.error('exchange failed', e)
  }
}

const startExchange = async () => {
  if (!canExchange.value) return
  if (!myItems.value.length) {
    await submitExchange(null)
    return
  }

  const labels = myItems.value.map((it: any) => it.title)
  uni.showActionSheet({
    itemList: labels,
    success: async (res) => {
      const selected = myItems.value[res.tapIndex]
      await submitExchange(selected?.id)
    }
  })
}

const startReply = (comment: any) => {
  replyTo.value = comment
}

const cancelReply = () => {
  replyTo.value = null
}

const submitComment = async () => {
  if (!commentText.value.trim()) return
  if (!ensureAuthed({ toast: '请先登录后评论' })) return
  try {
    const payload: any = { content: commentText.value }
    if (replyTo.value) payload.parent_id = replyTo.value.id
    await request.authPost(`/comments/${item.value.id}`, payload)
    uni.showToast({ title: '已发送', icon: 'success' })
    commentText.value = ''
    replyTo.value = null
    await loadComments(String(item.value.id))
  } catch (e) {
    console.error('submit comment failed', e)
  }
}

const formatDate = (iso: string) => {
  const d = new Date(iso)
  const hh = d.getHours().toString().padStart(2, '0')
  const mm = d.getMinutes().toString().padStart(2, '0')
  return `${d.getMonth() + 1}/${d.getDate()} ${hh}:${mm}`
}

onLoad(async (options: any) => {
  await loadOptions()
  if (options.id) {
    await Promise.all([loadDetail(options.id), loadComments(options.id)])
  }
  await loadMyItems()
})

onShow(async () => {
  if (item.value?.id) {
    await loadDetail(String(item.value.id))
  }
})
</script>

<style>
.page {
  min-height: 100vh;
  background: #f8fafc;
  padding-bottom: 170rpx;
}

.hero {
  position: relative;
}

.hero-swiper {
  width: 100%;
  height: 500rpx;
}

.hero-image {
  width: 100%;
  height: 100%;
}

.hero-mask {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  height: 140rpx;
  background: linear-gradient(180deg, rgba(0, 0, 0, 0.35), rgba(0, 0, 0, 0));
}

.hero-actions {
  position: absolute;
  left: 20rpx;
  right: 20rpx;
  top: 24rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.right-actions {
  display: flex;
  gap: 10rpx;
}

.icon-btn {
  width: 64rpx;
  height: 64rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.24);
  backdrop-filter: blur(6px);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36rpx;
  font-weight: 700;
}

.icon-btn.disabled {
  opacity: 0.5;
}

.icon-btn.fav {
  background: rgba(239, 68, 68, 0.9);
}

.content-card {
  margin: -44rpx 24rpx 14rpx;
  padding: 22rpx;
  border-radius: 22rpx;
  background: #fff;
  border: 1rpx solid #e2e8f0;
  position: relative;
  z-index: 3;
}

.title-row {
  display: flex;
  justify-content: space-between;
}

.title-side {
  flex: 1;
}

.category {
  display: inline-block;
  padding: 6rpx 12rpx;
  font-size: 20rpx;
  color: #9a3412;
  background: #ffedd5;
  border: 1rpx solid #fed7aa;
  border-radius: 10rpx;
}

.title {
  display: block;
  margin-top: 10rpx;
  font-size: 36rpx;
  color: #0f172a;
  font-weight: 800;
  line-height: 1.35;
}

.meta-line {
  margin-top: 10rpx;
  color: #64748b;
  font-size: 23rpx;
  display: flex;
  align-items: center;
}

.dot {
  margin: 0 10rpx;
}

.desc {
  display: block;
  margin-top: 14rpx;
  font-size: 25rpx;
  color: #334155;
  line-height: 1.55;
}

.specs {
  margin-top: 14rpx;
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
}

.spec {
  font-size: 22rpx;
  color: #475569;
  background: #f8fafc;
  border: 1rpx solid #e2e8f0;
  border-radius: 999rpx;
  padding: 8rpx 14rpx;
}

.flavors {
  margin-top: 14rpx;
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
}

.flavor {
  padding: 8rpx 14rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
  color: #9a3412;
  background: #ffedd5;
  border: 1rpx solid #fed7aa;
}

.flavor.voted {
  background: #ea580c;
  border-color: #ea580c;
  color: #fff;
}

.owner-card {
  margin-top: 18rpx;
  border-top: 1rpx solid #f1f5f9;
  padding-top: 16rpx;
  display: flex;
  align-items: center;
}

.owner-avatar {
  width: 72rpx;
  height: 72rpx;
  border-radius: 50%;
  background: #e2e8f0;
}

.owner-info {
  flex: 1;
  margin-left: 12rpx;
}

.owner-name {
  display: block;
  font-size: 26rpx;
  color: #0f172a;
  font-weight: 700;
}

.owner-tip {
  display: block;
  margin-top: 4rpx;
  font-size: 21rpx;
  color: #64748b;
}

.owner-btn {
  margin-left: 10rpx;
  padding: 10rpx 16rpx;
  border-radius: 999rpx;
  color: #fff;
  font-size: 22rpx;
}

.owner-btn.swap {
  background: #f97316;
}

.owner-btn.chat {
  background: #0f172a;
}

.comment-card {
  margin: 0 24rpx;
  border-radius: 20rpx;
  padding: 20rpx;
  background: #fff;
  border: 1rpx solid #e2e8f0;
}

.comment-title {
  display: block;
  font-size: 30rpx;
  color: #0f172a;
  font-weight: 700;
  margin-bottom: 14rpx;
}

.comment-item {
  border-left: 3rpx solid #e2e8f0;
  padding-left: 12rpx;
  margin-bottom: 14rpx;
}

.comment-user {
  display: block;
  color: #0f172a;
  font-size: 24rpx;
  font-weight: 600;
}

.comment-content {
  display: block;
  color: #334155;
  font-size: 25rpx;
  line-height: 1.5;
  margin-top: 6rpx;
}

.comment-meta {
  display: block;
  color: #94a3b8;
  font-size: 21rpx;
  margin-top: 6rpx;
}

.empty {
  text-align: center;
  color: #94a3b8;
  padding: 30rpx 0;
  font-size: 24rpx;
}

.input-wrap {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  background: #fff;
  border-top: 1rpx solid #e2e8f0;
  padding: 14rpx 20rpx calc(14rpx + env(safe-area-inset-bottom));
  z-index: 30;
}

.reply-banner {
  background: #fff7ed;
  color: #9a3412;
  border: 1rpx solid #fed7aa;
  border-radius: 12rpx;
  padding: 10rpx 14rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 22rpx;
  margin-bottom: 10rpx;
}

.cancel {
  color: #ea580c;
}

.input-row {
  display: flex;
  gap: 10rpx;
  align-items: center;
}

.comment-input {
  flex: 1;
  height: 76rpx;
  border-radius: 999rpx;
  border: 1rpx solid #e2e8f0;
  background: #f8fafc;
  padding: 0 18rpx;
  box-sizing: border-box;
  font-size: 24rpx;
}

.send {
  background: #f97316;
  color: #fff;
  border: none;
  border-radius: 999rpx;
  padding: 0 22rpx;
}

.not-local {
  text-align: center;
  color: #9a3412;
  background: #fff7ed;
  border: 1rpx solid #fed7aa;
  border-radius: 12rpx;
  padding: 14rpx;
  font-size: 23rpx;
}
</style>
