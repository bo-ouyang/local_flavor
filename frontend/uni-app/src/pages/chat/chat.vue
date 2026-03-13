<template>
  <view class="page">
    <view v-if="!isAuthed" class="guest">
      <text class="guest-title">登录后可聊天</text>
      <button type="primary" size="mini" @click="goLogin()">去登录</button>
    </view>

    <template v-else>
      <view class="chat-body">
        <scroll-view scroll-y class="history" :scroll-top="scrollTop">
          <view class="msg-list">
            <view class="msg-item" :class="{ self: msg.sender_id === userStore.userInfo.id }" v-for="msg in messages" :key="msg.id">
              <view class="bubble">
                <text v-if="msg.content" class="bubble-text">{{ msg.content }}</text>
                <view class="item-card" v-if="msg.item" @click="goToDetail(msg.item.id)">
                  <image :src="msg.item.images?.[0]" mode="aspectFill" class="item-cover" />
                  <text class="item-title">{{ msg.item.title }}</text>
                </view>
                <text class="msg-time">{{ formatMessageTime(msg.created_at) }}</text>
              </view>
            </view>
          </view>
        </scroll-view>

        <view class="input-wrap">
          <view class="util" @click="toggleMyItems">+</view>
          <input
            v-model="text"
            class="ipt"
            confirm-type="send"
            @confirm="sendText"
            placeholder="输入消息..."
          />
          <button size="mini" class="send" :loading="sending" @click="sendText">发送</button>
        </view>

        <view class="drawer" v-if="showMyItems">
          <scroll-view scroll-x class="drawer-scroll">
            <view class="drawer-item" v-for="it in myItems" :key="it.id" @click="sendItemCard(it)">
              <image :src="it.images?.[0]" mode="aspectFill" class="drawer-cover" />
              <text class="drawer-title">{{ it.title }}</text>
            </view>
          </scroll-view>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { onHide, onLoad, onShow, onUnload } from '@dcloudio/uni-app'
import { useUserStore } from '@/stores/user'
import request from '@/utils/request'
import { goLogin } from '@/utils/auth'

const userStore = useUserStore()
const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL || 'http://127.0.0.1:8001/api/v1'
const WS_BASE = API_BASE.replace(/^http/, 'ws').replace(/\/api\/v1\/?$/, '')
const isAuthed = computed(() => !!userStore.token)
const conversationId = ref(0)
const targetId = ref(0)
const messages = ref<any[]>([])
const text = ref('')
const scrollTop = ref(0)
const showMyItems = ref(false)
const myItems = ref<any[]>([])
const sending = ref(false)
const wsConnected = ref(false)
let socketTask: UniApp.SocketTask | null = null
let pollingTimer: any = null

const sortBySeq = (list: any[]) => {
  return [...list].sort((a, b) => (a.seq || 0) - (b.seq || 0))
}

const mergeMessages = (incoming: any[]) => {
  const map = new Map<number, any>()
  messages.value.forEach((m) => map.set(m.id, m))
  incoming.forEach((m) => map.set(m.id, m))
  messages.value = sortBySeq(Array.from(map.values()))
}

const scrollToBottom = () => {
  nextTick(() => {
    scrollTop.value = 9999999
  })
}

const loadHistory = async () => {
  if (!conversationId.value) return
  try {
    const res: any = await request.authGet(`/chat/conversations/${conversationId.value}/messages`, { limit: 50 })
    messages.value = sortBySeq(res || [])
    scrollToBottom()
    await ackRead()
  } catch (e) {
    console.error('load history failed', e)
  }
}

const pollLatest = async () => {
  if (!conversationId.value || wsConnected.value) return
  try {
    const res: any = await request.authGet(
      `/chat/conversations/${conversationId.value}/messages`,
      { limit: 30 },
      { skipToast: true }
    )
    mergeMessages(res || [])
    scrollToBottom()
    await ackRead()
  } catch (e) {
    console.error('poll latest failed', e)
  }
}

const ackRead = async () => {
  if (!conversationId.value || !messages.value.length) return
  const latestSeq = messages.value[messages.value.length - 1]?.seq || 0
  try {
    await request.authPost(
      `/chat/conversations/${conversationId.value}/read`,
      { seq: latestSeq },
      { skipToast: true }
    )
  } catch (e) {
    console.error('ack read failed', e)
  }
}

const loadMyItems = async () => {
  if (!isAuthed.value || !userStore.userInfo.id) {
    myItems.value = []
    return
  }
  try {
    const res: any = await request.get('/items/', { publisher_id: userStore.userInfo.id, limit: 50 }, { skipToast: true })
    myItems.value = res || []
  } catch (e) {
    console.error('load my items failed', e)
  }
}

const ensureConversation = async (itemId?: number) => {
  if (!targetId.value) return
  const payload: any = { target_id: targetId.value }
  if (itemId) payload.item_id = itemId
  const conv: any = await request.authPost('/chat/conversations/ensure', payload)
  conversationId.value = conv.conversation_id
}

const sendMessage = async (payload: any) => {
  if (!conversationId.value || sending.value) return
  sending.value = true
  try {
    const body = {
      conversation_id: conversationId.value,
      client_msg_id: `local-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      ...payload
    }
    const msg: any = await request.authPost('/chat/messages', body)
    mergeMessages([msg])
    scrollToBottom()
    await ackRead()
  } catch (e) {
    console.error('send message failed', e)
  } finally {
    sending.value = false
  }
}

const sendText = async () => {
  const value = text.value.trim()
  if (!value) return
  await sendMessage({
    msg_type: 'text',
    content: value
  })
  text.value = ''
}

const sendItemCard = async (item: any) => {
  await sendMessage({
    msg_type: 'item_card',
    content: `[分享商品] ${item.title}`,
    item_id: item.id
  })
  showMyItems.value = false
}

const toggleMyItems = () => {
  showMyItems.value = !showMyItems.value
}

const goToDetail = (id: number) => {
  uni.navigateTo({ url: `/pages/detail/detail?id=${id}` })
}

const formatMessageTime = (iso?: string) => {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const hh = d.getHours().toString().padStart(2, '0')
  const mm = d.getMinutes().toString().padStart(2, '0')
  return `${d.getMonth() + 1}/${d.getDate()} ${hh}:${mm}`
}

const startPolling = () => {
  if (pollingTimer) clearInterval(pollingTimer)
  pollingTimer = setInterval(() => {
    pollLatest()
  }, 5000)
}

const stopPolling = () => {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

const handleSocketPayload = async (payload: any) => {
  if (!payload || typeof payload !== 'object') return
  if (payload.event === 'message.created' && payload.message) {
    mergeMessages([payload.message])
    scrollToBottom()
    await ackRead()
  }
}

const closeSocket = () => {
  wsConnected.value = false
  if (socketTask) {
    try {
      socketTask.close({})
    } catch (e) {
      console.error('close socket failed', e)
    }
    socketTask = null
  }
}

const connectSocket = () => {
  if (!conversationId.value || !userStore.token || socketTask) return
  const url = `${WS_BASE}/ws/chat/conversations/${conversationId.value}/?token=${encodeURIComponent(userStore.token)}`
  socketTask = uni.connectSocket({
    url,
    complete: () => {}
  })

  socketTask.onOpen(() => {
    wsConnected.value = true
  })

  socketTask.onMessage((res) => {
    try {
      const payload = JSON.parse((res?.data as string) || '{}')
      handleSocketPayload(payload)
    } catch (e) {
      console.error('invalid socket payload', e)
    }
  })

  socketTask.onClose(() => {
    wsConnected.value = false
    socketTask = null
  })

  socketTask.onError((err) => {
    console.error('socket error', err)
    wsConnected.value = false
    socketTask = null
  })
}

onLoad(async (options: any) => {
  if (!isAuthed.value) return

  if (options?.nickname) {
    try {
      uni.setNavigationBarTitle({ title: decodeURIComponent(options.nickname) })
    } catch {
      uni.setNavigationBarTitle({ title: options.nickname || '聊天' })
    }
  }

  if (options?.conversationId) {
    conversationId.value = Number(options.conversationId)
  } else if (options?.targetId) {
    targetId.value = Number(options.targetId)
    await ensureConversation(options?.itemId ? Number(options.itemId) : undefined)
  }

  if (conversationId.value) {
    await Promise.all([loadHistory(), loadMyItems()])
    connectSocket()
    startPolling()
  }
})

onShow(async () => {
  if (!isAuthed.value) return
  if (conversationId.value) {
    if (!wsConnected.value) connectSocket()
    await pollLatest()
  }
})

onHide(() => {
  closeSocket()
})

onUnload(() => {
  closeSocket()
  stopPolling()
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

.chat-body {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.history {
  flex: 1;
  padding: 20rpx;
  box-sizing: border-box;
}

.msg-item {
  display: flex;
  margin-bottom: 16rpx;
}

.msg-item.self {
  justify-content: flex-end;
}

.bubble {
  max-width: 74%;
  border-radius: 22rpx;
  padding: 14rpx 16rpx;
  background: #fff;
  border: 1rpx solid #e2e8f0;
}

.msg-item.self .bubble {
  background: #f97316;
  border-color: #f97316;
}

.bubble-text {
  color: #1e293b;
  font-size: 26rpx;
  line-height: 1.45;
}

.msg-item.self .bubble-text {
  color: #fff;
}

.msg-time {
  display: block;
  margin-top: 6rpx;
  text-align: right;
  color: #94a3b8;
  font-size: 19rpx;
}

.msg-item.self .msg-time {
  color: #ffedd5;
}

.item-card {
  margin-top: 8rpx;
  border-radius: 12rpx;
  background: rgba(255, 255, 255, 0.9);
  overflow: hidden;
}

.item-cover {
  width: 220rpx;
  height: 140rpx;
  display: block;
}

.item-title {
  display: block;
  padding: 8rpx;
  font-size: 22rpx;
  color: #334155;
}

.input-wrap {
  background: #fff;
  border-top: 1rpx solid #e2e8f0;
  display: flex;
  align-items: center;
  gap: 10rpx;
  padding: 12rpx 16rpx;
}

.util {
  width: 46rpx;
  text-align: center;
  font-size: 40rpx;
  color: #64748b;
}

.ipt {
  flex: 1;
  height: 72rpx;
  border-radius: 999rpx;
  border: 1rpx solid #e2e8f0;
  background: #f8fafc;
  padding: 0 18rpx;
  box-sizing: border-box;
  font-size: 25rpx;
}

.send {
  border-radius: 999rpx;
  background: #f97316;
  color: #fff;
  border: none;
  padding: 0 18rpx;
}

.drawer {
  background: #fff;
  border-top: 1rpx solid #e2e8f0;
  padding: 14rpx;
}

.drawer-scroll {
  white-space: nowrap;
}

.drawer-item {
  display: inline-block;
  width: 170rpx;
  margin-right: 12rpx;
}

.drawer-cover {
  width: 170rpx;
  height: 110rpx;
  border-radius: 10rpx;
  background: #e2e8f0;
}

.drawer-title {
  display: block;
  margin-top: 8rpx;
  font-size: 21rpx;
  color: #334155;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
