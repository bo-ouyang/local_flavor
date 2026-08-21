<template>
  <view class="page">
    <view v-if="!isAuthed" class="guest">
      <text class="guest-title">登录后可查看交换记录</text>
      <button :type="('primary' as any)" size="mini" @click="goLogin()">去登录</button>
    </view>

    <template v-else>
      <view class="tabs">
        <view class="tab" :class="{ active: role === 'all' }" @click="switchRole('all')">全部</view>
        <view class="tab" :class="{ active: role === 'received' }" @click="switchRole('received')">收到</view>
        <view class="tab" :class="{ active: role === 'sent' }" @click="switchRole('sent')">发起</view>
      </view>

      <view class="list" v-if="requests.length">
        <view class="card" v-for="req in requests" :key="req.id">
          <view class="row">
            <text class="id">请求 #{{ req.id }}</text>
            <text class="status" :class="req.status">{{ statusText(req.status) }}</text>
          </view>
          <text class="meta">发起人：{{ resolveUserName(req.requester_id, req) }} · 接收人：{{ resolveUserName(req.owner_id, req) }}</text>
          <text class="meta">目标商品：{{ resolveItemTitle(req.requested_item_id) }}</text>
          <text class="meta" v-if="req.offered_item_id">发起方商品：{{ resolveItemTitle(req.offered_item_id) }}</text>
          <text class="meta">时间：{{ formatDateTime(req.created_at) }}</text>
          <text class="meta" v-if="req.message">留言：{{ req.message }}</text>

          <view class="jump" @click="goRequesterItem(req)">
            查看发起方商品详情
          </view>

          <view class="actions" v-if="showActions(req)">
            <button size="mini" :type="('primary' as any)" @click="updateStatus(req.id, 'accepted')">同意</button>
            <button size="mini" @click="updateStatus(req.id, 'rejected')">拒绝</button>
          </view>

          <view class="actions" v-if="showCancel(req)">
            <button size="mini" @click="updateStatus(req.id, 'cancelled')">取消</button>
          </view>

          <view class="actions" v-if="showComplete(req)">
            <button size="mini" :type="('warn' as any)" @click="updateStatus(req.id, 'completed')">完成交换</button>
          </view>
        </view>
      </view>
      <view v-else class="empty">暂无交换记录</view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import request from '@/utils/request'
import { useUserStore } from '@/stores/user'
import { goLogin } from '@/utils/auth'

const userStore = useUserStore()
const isAuthed = computed(() => !!userStore.token)
const role = ref<'all' | 'sent' | 'received'>('all')
const requests = ref<any[]>([])
const itemInfoMap = ref<Record<number, any>>({})
const userNameMap = ref<Record<number, string>>({})

const normalizeId = (value: any) => {
  const num = Number(value)
  return Number.isFinite(num) && num > 0 ? num : 0
}

const resolveItemTitle = (itemId: number) => {
  const id = normalizeId(itemId)
  if (!id) return '未知商品'
  const item = itemInfoMap.value[id]
  return item?.title || '未知商品'
}

const inferUserNameFromRequest = (userId: number, req: any) => {
  if (!req) return ''
  const uid = normalizeId(userId)
  if (!uid) return ''
  if (uid === normalizeId(req.owner_id)) {
    const requested = itemInfoMap.value[normalizeId(req.requested_item_id)]
    if (requested?.publisher?.id === uid) {
      return requested.publisher.nickname || '未知用户'
    }
  }
  if (uid === normalizeId(req.requester_id)) {
    const offered = itemInfoMap.value[normalizeId(req.offered_item_id)]
    if (offered?.publisher?.id === uid) {
      return offered.publisher.nickname || '未知用户'
    }
  }
  return ''
}

const resolveUserName = (userId: number, req?: any) => {
  const uid = normalizeId(userId)
  if (!uid) return '未知用户'
  if (userNameMap.value[uid]) return userNameMap.value[uid]
  const inferred = inferUserNameFromRequest(uid, req)
  if (inferred) return inferred
  if (uid === normalizeId(userStore.userInfo.id)) {
    return userStore.userInfo.nickname || '我'
  }
  return '未知用户'
}

const hydrateRequestMeta = async (rows: any[]) => {
  const idSet = new Set<number>()
  rows.forEach((req: any) => {
    const requestedId = normalizeId(req.requested_item_id)
    const offeredId = normalizeId(req.offered_item_id)
    if (requestedId) idSet.add(requestedId)
    if (offeredId) idSet.add(offeredId)
  })
  const ids = Array.from(idSet)
  if (!ids.length) {
    itemInfoMap.value = {}
    return
  }

  const tasks = ids.map((id) =>
    request
      .get(`/items/${id}`, undefined, { skipToast: true })
      .then((data: any) => ({ id, data }))
      .catch(() => null)
  )
  const results = await Promise.all(tasks)

  const nextItemMap: Record<number, any> = {}
  const nextUserMap: Record<number, string> = {
    ...userNameMap.value,
  }
  const selfId = normalizeId(userStore.userInfo.id)
  if (selfId) {
    nextUserMap[selfId] = userStore.userInfo.nickname || '我'
  }

  results.forEach((entry) => {
    if (!entry || !entry.data) return
    nextItemMap[entry.id] = entry.data
    const publisher = entry.data?.publisher
    const publisherId = normalizeId(publisher?.id)
    if (publisherId) {
      nextUserMap[publisherId] = publisher?.nickname || '未知用户'
    }
  })

  rows.forEach((req: any) => {
    const ownerId = normalizeId(req.owner_id)
    const requesterId = normalizeId(req.requester_id)
    if (ownerId && !nextUserMap[ownerId]) {
      const requested = nextItemMap[normalizeId(req.requested_item_id)]
      if (requested?.publisher?.id === ownerId) {
        nextUserMap[ownerId] = requested.publisher.nickname || '未知用户'
      }
    }
    if (requesterId && !nextUserMap[requesterId]) {
      const offered = nextItemMap[normalizeId(req.offered_item_id)]
      if (offered?.publisher?.id === requesterId) {
        nextUserMap[requesterId] = offered.publisher.nickname || '未知用户'
      }
    }
  })

  itemInfoMap.value = nextItemMap
  userNameMap.value = nextUserMap
}

const loadData = async () => {
  if (!isAuthed.value) {
    requests.value = []
    itemInfoMap.value = {}
    return
  }
  try {
    const res: any = await request.authGet('/exchange/requests', { role: role.value })
    const rows = Array.isArray(res) ? res : []
    requests.value = rows
    await hydrateRequestMeta(rows)
  } catch (e) {
    console.error('load exchange requests failed', e)
  }
}

const switchRole = (nextRole: 'all' | 'sent' | 'received') => {
  role.value = nextRole
  loadData()
}

const statusText = (status: string) => {
  const map: Record<string, string> = {
    pending: '待处理',
    accepted: '已同意',
    rejected: '已拒绝',
    cancelled: '已取消',
    completed: '已完成'
  }
  return map[status] || status
}

const formatDateTime = (iso?: string) => {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '-'
  const hh = d.getHours().toString().padStart(2, '0')
  const mm = d.getMinutes().toString().padStart(2, '0')
  return `${d.getFullYear()}-${(d.getMonth() + 1).toString().padStart(2, '0')}-${d
    .getDate()
    .toString()
    .padStart(2, '0')} ${hh}:${mm}`
}

const goRequesterItem = (req: any) => {
  const itemId = req.offered_item_id
  if (!itemId) {
    uni.showToast({ title: '该请求未附带发起方商品', icon: 'none' })
    return
  }
  uni.navigateTo({ url: `/pages/detail/detail?id=${itemId}` })
}

const showActions = (req: any) => req.status === 'pending' && req.owner_id === userStore.userInfo.id
const showCancel = (req: any) => req.status === 'pending' && req.requester_id === userStore.userInfo.id
const showComplete = (req: any) =>
  req.status === 'accepted' && (req.owner_id === userStore.userInfo.id || req.requester_id === userStore.userInfo.id)

const updateStatus = async (id: number, status: string) => {
  try {
    await request.authPut(`/exchange/requests/${id}/status`, { status })
    uni.showToast({ title: '状态已更新', icon: 'success' })
    loadData()
  } catch (e) {
    console.error('update exchange status failed', e)
  }
}

onShow(() => {
  loadData()
})
</script>

<style>
.page {
  min-height: 100vh;
  background: #f8fafc;
  padding: 16rpx;
}

.guest {
  background: #fff;
  border-radius: 14rpx;
  border: 1rpx solid #e2e8f0;
  padding: 24rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.guest-title {
  font-size: 26rpx;
  color: #475569;
}

.tabs {
  display: flex;
  background: #e2e8f0;
  border-radius: 12rpx;
  padding: 6rpx;
  margin-bottom: 14rpx;
}

.tab {
  flex: 1;
  text-align: center;
  padding: 14rpx 0;
  border-radius: 10rpx;
  color: #475569;
  font-size: 23rpx;
}

.tab.active {
  background: #fff;
  color: #0f172a;
  font-weight: 700;
}

.card {
  background: #fff;
  border: 1rpx solid #e2e8f0;
  border-radius: 16rpx;
  padding: 18rpx;
  margin-bottom: 12rpx;
}

.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10rpx;
}

.id {
  color: #0f172a;
  font-size: 26rpx;
  font-weight: 700;
}

.meta {
  display: block;
  color: #64748b;
  font-size: 23rpx;
  margin-bottom: 6rpx;
}

.status {
  font-size: 22rpx;
  font-weight: 700;
}

.status.pending { color: #d97706; }
.status.accepted { color: #16a34a; }
.status.rejected { color: #ef4444; }
.status.cancelled { color: #94a3b8; }
.status.completed { color: #2563eb; }

.jump {
  margin-top: 8rpx;
  background: #fff7ed;
  border: 1rpx solid #fed7aa;
  color: #c2410c;
  font-size: 22rpx;
  border-radius: 10rpx;
  padding: 10rpx 12rpx;
}

.actions {
  margin-top: 12rpx;
  display: flex;
  gap: 10rpx;
}

.empty {
  text-align: center;
  color: #94a3b8;
  margin-top: 100rpx;
  font-size: 24rpx;
}
</style>
