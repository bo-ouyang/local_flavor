<template>
  <view class="page">
    <view v-if="!isAuthed" class="guest">
      <text class="guest-title">登录后可查看私聊消息</text>
      <button :type="('primary' as any)" size="mini" @click="goLogin()">去登录</button>
    </view>

    <template v-else>
      <view class="list" v-if="conversations.length">
        <view class="item" v-for="conv in conversations" :key="conv.conversation_id" @click="goToChat(conv)">
          <image :src="conv.contact.avatar || defaultAvatar" class="avatar" mode="aspectFill" />
          <view class="middle">
            <view class="top">
              <text class="name">{{ conv.contact.nickname || ('用户' + conv.contact.id) }}</text>
              <text class="time">{{ formatTime(conv.last_message?.created_at) }}</text>
            </view>
            <view class="bottom">
              <text class="msg">{{ conv.last_message?.content || '暂无消息' }}</text>
              <view class="badge" v-if="conv.unread_count > 0">{{ conv.unread_count }}</view>
            </view>
          </view>
        </view>
      </view>
      <view v-else class="empty">暂无会话</view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import request from '@/utils/request'
import { useUserStore } from '@/stores/user'
import { goLogin } from '@/utils/auth'

const userStore = useUserStore()
const isAuthed = computed(() => !!userStore.token)
const conversations = ref<any[]>([])
const defaultAvatar = 'https://dummyimage.com/200x200/e2e8f0/94a3b8&text=User'

const loadConversations = async () => {
  if (!isAuthed.value) {
    conversations.value = []
    return
  }
  try {
    const res: any = await request.authGet('/chat/conversations')
    conversations.value = Array.isArray(res) ? res : []
  } catch (e) {
    console.error('load conversations failed', e)
  }
}

const goToChat = (conv: any) => {
  const nickname = conv?.contact?.nickname || `用户${conv?.contact?.id || ''}`
  uni.navigateTo({
    url: `/pages/chat/chat?conversationId=${conv.conversation_id}&nickname=${encodeURIComponent(nickname)}`
  })
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

onShow(() => {
  loadConversations()
})

onPullDownRefresh(async () => {
  await loadConversations()
  uni.stopPullDownRefresh()
})
</script>

<style>
.page {
  min-height: 100vh;
  background: #f8fafc;
}

.guest {
  margin: 20rpx;
  background: #fff;
  border: 1rpx solid #e2e8f0;
  border-radius: 14rpx;
  padding: 24rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.guest-title {
  color: #475569;
  font-size: 26rpx;
}

.list {
  margin-top: 12rpx;
}

.item {
  margin: 0 16rpx 10rpx;
  border-radius: 16rpx;
  border: 1rpx solid #e2e8f0;
  background: #fff;
  padding: 16rpx;
  display: flex;
  align-items: center;
}

.avatar {
  width: 92rpx;
  height: 92rpx;
  border-radius: 14rpx;
  background: #e2e8f0;
}

.middle {
  flex: 1;
  margin-left: 14rpx;
  min-width: 0;
}

.top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.name {
  color: #0f172a;
  font-size: 28rpx;
  font-weight: 700;
}

.time {
  color: #94a3b8;
  font-size: 21rpx;
}

.bottom {
  margin-top: 8rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.msg {
  flex: 1;
  color: #64748b;
  font-size: 24rpx;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.badge {
  margin-left: 10rpx;
  min-width: 36rpx;
  height: 36rpx;
  border-radius: 999rpx;
  background: #ef4444;
  color: #fff;
  font-size: 20rpx;
  text-align: center;
  line-height: 36rpx;
  padding: 0 8rpx;
}

.empty {
  margin-top: 200rpx;
  text-align: center;
  color: #94a3b8;
  font-size: 24rpx;
}
</style>
