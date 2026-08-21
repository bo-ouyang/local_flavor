<template>
  <view class="page">
    <view class="header">
      <text class="header-title">发布交流</text>
      <text class="header-sub">只有完成过交换，才能分享这次收到的特产体验</text>
    </view>

    <view class="panel">
      <view class="notice">
        <text class="notice-title">发布规则</text>
        <text class="notice-text">1. 发布前必须有已完成交换</text>
        <text class="notice-text">2. 必须选择自己交换过的特产</text>
        <text class="notice-text">3. 其他用户只有参与过该特产交换才可评论</text>
      </view>

      <view v-if="needsLogin" class="login-box">
        <text class="login-title">登录后可发布社区交流</text>
        <text class="login-desc">登录后系统会读取你已完成交换的特产，并限制只能围绕这些特产发帖。</text>
        <view class="login-btn" @click="goLoginPage">去登录</view>
      </view>

      <view class="block">
        <text class="block-label">关联已交换特产</text>
        <picker v-if="eligibleItems.length" :range="itemLabels" @change="onItemChange">
          <view class="picker-box">
            {{ selectedItem?.title || '请选择你交换过的特产' }}
          </view>
        </picker>
        <view v-else class="empty-box">
          <text class="empty-title">还没有可发布的特产</text>
          <text class="empty-desc">只有在交换完成后，才能来社区分享收到的特产</text>
        </view>

        <view v-if="selectedItem" class="selected-card">
          <image :src="selectedCover" mode="aspectFill" class="selected-cover" />
          <view class="selected-info">
            <text class="selected-title">{{ selectedItem.title }}</text>
            <text class="selected-meta">{{ selectedItem.city || selectedItem.province || '未知地区' }}</text>
          </view>
        </view>
      </view>

      <view class="block">
        <text class="block-label">交流内容</text>
        <textarea
          v-model="content"
          class="textarea"
          maxlength="2000"
          placeholder="说说你收到的特产味道如何、包装体验、交换感受..."
          :disabled="needsLogin || !eligibleItems.length"
        />
      </view>

      <view class="block">
        <view class="image-head">
          <text class="block-label">交流配图</text>
          <text class="image-tip">最多 9 张</text>
        </view>
        <view class="image-grid">
          <view
            v-for="(img, index) in images"
            :key="img"
            class="image-item"
            @click="removeImage(index)"
          >
            <image :src="img" mode="aspectFill" class="upload-image" />
            <view class="remove-badge">×</view>
          </view>
          <view v-if="images.length < 9 && !needsLogin && eligibleItems.length" class="upload-slot" @click="chooseImage">
            <text class="upload-plus">+</text>
            <text class="upload-text">添加图片</text>
          </view>
        </view>
      </view>

      <button
        class="submit-btn"
        :disabled="!canSubmit"
        :loading="submitting"
        @click="submitPost"
      >
        发布交流
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import request from '@/utils/request'
import { ensureAuthed, goLogin } from '@/utils/auth'
import { useUserStore } from '@/stores/user'
import { authUploadFile } from '@/utils/upload'

const userStore = useUserStore()
const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL || 'http://127.0.0.1:8001/api/v1'
const API_ORIGIN = API_BASE.replace(/\/api\/v1\/?$/, '')

const eligibleItems = ref<any[]>([])
const selectedIndex = ref(0)
const content = ref('')
const images = ref<string[]>([])
const submitting = ref(false)
const needsLogin = ref(false)

const itemLabels = computed(() => eligibleItems.value.map((item: any) => item.title))
const selectedItem = computed(() => eligibleItems.value[selectedIndex.value] || null)
const selectedCover = computed(() => {
  if (Array.isArray(selectedItem.value?.images) && selectedItem.value.images.length) {
    return selectedItem.value.images[0]
  }
  return 'https://dummyimage.com/400x300/f1f5f9/94a3b8&text=Treasure'
})
const canSubmit = computed(() => !!selectedItem.value && !!content.value.trim() && !submitting.value)

const loadEligibleItems = async () => {
  if (!userStore.token) {
    needsLogin.value = true
    eligibleItems.value = []
    return
  }
  try {
    const res: any = await request.authGet('/community/eligible-items')
    needsLogin.value = false
    eligibleItems.value = Array.isArray(res) ? res : []
    if (selectedIndex.value >= eligibleItems.value.length) {
      selectedIndex.value = 0
    }
  } catch (error) {
    console.error('load eligible community items failed', error)
  }
}

const onItemChange = (event: any) => {
  selectedIndex.value = Number(event.detail.value || 0)
}

const goLoginPage = () => {
  goLogin('/pages/community/create')
}

const chooseImage = () => {
  if (!ensureAuthed({ toast: '请先登录后上传图片', redirect: '/pages/community/create' })) return
  uni.chooseImage({
    count: 9 - images.value.length,
    sizeType: ['compressed'],
    sourceType: ['album', 'camera'],
    success: async (res) => {
      const paths = Array.isArray(res.tempFilePaths)
        ? res.tempFilePaths
        : (res.tempFilePaths ? [res.tempFilePaths] : [])
      await uploadImages(paths)
    }
  })
}

const uploadImages = async (paths: string[]) => {
  uni.showLoading({ title: '上传中...' })
  for (const path of paths) {
    try {
      const data = await authUploadFile({ url: `${API_BASE}/upload/`, filePath: path, name: 'file' })
      if (data?.code !== 0 || !data?.data?.url) throw new Error('upload failed')
      images.value.push(`${API_ORIGIN}${data.data.url}`)
    } catch (error) {
      console.error('upload community image failed', error)
      uni.showToast({ title: '图片上传失败', icon: 'none' })
    }
  }
  uni.hideLoading()
}

const removeImage = (index: number) => {
  images.value.splice(index, 1)
}

const resetForm = () => {
  content.value = ''
  images.value = []
}

const submitPost = async () => {
  if (!ensureAuthed({ toast: '请先登录后发布交流', redirect: '/pages/community/create' })) return
  if (!selectedItem.value) {
    uni.showToast({ title: '请先选择已交换特产', icon: 'none' })
    return
  }
  if (!content.value.trim()) {
    uni.showToast({ title: '请输入交流内容', icon: 'none' })
    return
  }

  submitting.value = true
  try {
    const created: any = await request.authPost('/community/posts', {
      item_id: selectedItem.value.id,
      content: content.value.trim(),
      images: images.value
    })
    uni.showToast({ title: '已提交审核', icon: 'success' })
    resetForm()
    setTimeout(() => {
      uni.redirectTo({ url: `/pages/community/detail?id=${created.id}` })
    }, 300)
  } catch (error) {
    console.error('publish community post failed', error)
  } finally {
    submitting.value = false
  }
}

onShow(async () => {
  await loadEligibleItems()
})
</script>

<style>
.page {
  min-height: 100vh;
  background:
    radial-gradient(circle at top right, rgba(249, 115, 22, 0.18), transparent 22%),
    linear-gradient(180deg, #fff7ed 0%, #f8fafc 26%, #f8fafc 100%);
}

.header {
  padding: 28rpx 28rpx 16rpx;
}

.header-title {
  display: block;
  font-size: 40rpx;
  font-weight: 800;
  color: #0f172a;
}

.header-sub {
  display: block;
  margin-top: 8rpx;
  font-size: 23rpx;
  color: #64748b;
  line-height: 1.5;
}

.panel {
  padding: 0 22rpx 36rpx;
}

.notice,
.block {
  background: rgba(255, 255, 255, 0.94);
  border: 1rpx solid #e2e8f0;
  border-radius: 24rpx;
  box-shadow: 0 12rpx 34rpx rgba(15, 23, 42, 0.06);
}

.notice {
  padding: 20rpx;
  margin-bottom: 16rpx;
  background: linear-gradient(135deg, #fff7ed, #ffffff);
  border-color: #fed7aa;
}

.login-box {
  padding: 22rpx 20rpx;
  margin-bottom: 16rpx;
  border-radius: 24rpx;
  background: linear-gradient(135deg, #fff, #fff7ed);
  border: 1rpx solid #fed7aa;
  box-shadow: 0 12rpx 28rpx rgba(249, 115, 22, 0.08);
}

.login-title {
  display: block;
  font-size: 28rpx;
  font-weight: 800;
  color: #9a3412;
}

.login-desc {
  display: block;
  margin-top: 8rpx;
  font-size: 22rpx;
  line-height: 1.6;
  color: #c2410c;
}

.login-btn {
  margin-top: 16rpx;
  width: 180rpx;
  height: 68rpx;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #f97316, #f59e0b);
  color: #fff;
  font-size: 24rpx;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.notice-title {
  display: block;
  font-size: 26rpx;
  color: #9a3412;
  font-weight: 800;
  margin-bottom: 8rpx;
}

.notice-text {
  display: block;
  font-size: 22rpx;
  color: #c2410c;
  line-height: 1.7;
}

.block {
  padding: 20rpx;
  margin-bottom: 16rpx;
}

.block-label {
  display: block;
  margin-bottom: 12rpx;
  font-size: 25rpx;
  font-weight: 700;
  color: #334155;
}

.picker-box,
.textarea {
  width: 100%;
  box-sizing: border-box;
  border-radius: 18rpx;
  border: 1rpx solid #e2e8f0;
  background: #f8fafc;
}

.picker-box {
  min-height: 82rpx;
  padding: 0 20rpx;
  display: flex;
  align-items: center;
  font-size: 25rpx;
  color: #0f172a;
}

.selected-card {
  margin-top: 16rpx;
  display: flex;
  gap: 14rpx;
  align-items: center;
  padding: 14rpx;
  border-radius: 20rpx;
  background: #fff7ed;
  border: 1rpx solid #fed7aa;
}

.selected-cover {
  width: 120rpx;
  height: 120rpx;
  border-radius: 16rpx;
  background: #e2e8f0;
  flex-shrink: 0;
}

.selected-info {
  flex: 1;
}

.selected-title {
  display: block;
  font-size: 28rpx;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.4;
}

.selected-meta {
  display: block;
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #64748b;
}

.textarea {
  min-height: 260rpx;
  padding: 18rpx;
  font-size: 26rpx;
  color: #0f172a;
  line-height: 1.6;
}

.image-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12rpx;
}

.image-tip {
  font-size: 21rpx;
  color: #94a3b8;
}

.image-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}

.image-item,
.upload-slot {
  width: 204rpx;
  height: 160rpx;
  border-radius: 16rpx;
  overflow: hidden;
  position: relative;
}

.image-item {
  border: 1rpx solid #e2e8f0;
}

.upload-image {
  width: 100%;
  height: 100%;
  background: #e2e8f0;
}

.remove-badge {
  position: absolute;
  right: 8rpx;
  top: 8rpx;
  width: 34rpx;
  height: 34rpx;
  line-height: 34rpx;
  text-align: center;
  border-radius: 50%;
  background: rgba(15, 23, 42, 0.5);
  color: #fff;
  font-size: 24rpx;
}

.upload-slot {
  border: 2rpx dashed #cbd5e1;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.upload-plus {
  font-size: 44rpx;
  line-height: 1;
  color: #94a3b8;
}

.upload-text {
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #64748b;
}

.submit-btn {
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 18rpx;
  border: none;
  background: linear-gradient(135deg, #f97316, #f59e0b);
  color: #fff;
  font-size: 30rpx;
  font-weight: 800;
}

.submit-btn[disabled] {
  opacity: 0.55;
}

.empty-box {
  padding: 22rpx 18rpx;
  border-radius: 18rpx;
  background: #fff7ed;
  border: 1rpx solid #fed7aa;
}

.empty-title {
  display: block;
  font-size: 24rpx;
  font-weight: 700;
  color: #9a3412;
}

.empty-desc {
  display: block;
  margin-top: 8rpx;
  font-size: 22rpx;
  line-height: 1.5;
  color: #c2410c;
}
</style>
