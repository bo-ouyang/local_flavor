<template>
  <view class="page">
    <view class="topbar">
      <text class="topbar-title">发布特产</text>
      <text class="topbar-sub">分享你的家乡味道</text>
    </view>

    <view class="panel">
      <view class="field">
        <text class="label">特产照片</text>
        <view class="image-area">
          <view class="image-item" v-for="(img, index) in form.images" :key="index" @click="removeImage(index)">
            <image :src="img" mode="aspectFill" class="image" />
            <view class="remove">×</view>
          </view>
          <view class="upload-slot" v-if="form.images.length < 3" @click="chooseImage">
            <text class="upload-plus">+</text>
            <text class="upload-tip">上传照片</text>
          </view>
        </view>
      </view>

      <view class="field">
        <text class="label">名称</text>
        <input v-model="form.title" class="input" placeholder="例如：正宗四川腊肠" />
      </view>

      <view class="grid-2">
        <view class="field card-field">
          <text class="label">分类</text>
          <picker :range="categoryLabels" @change="onCategoryChange">
            <view class="picker-box">{{ optionLabel(categories, form.category) || '请选择分类' }}</view>
          </picker>
        </view>
        <view class="field card-field">
          <text class="label">时令</text>
          <picker :range="seasonLabels" @change="onSeasonChange">
            <view class="picker-box">{{ optionLabel(seasons, form.season) || '请选择时令' }}</view>
          </picker>
        </view>
      </view>

      <view class="grid-2">
        <view class="field card-field">
          <text class="label">保质期</text>
          <picker :range="shelfLifeLabels" @change="onShelfLifeChange">
            <view class="picker-box">{{ optionLabel(shelfLives, form.shelf_life) || '请选择保质期' }}</view>
          </picker>
        </view>
        <view class="field card-field">
          <text class="label">便携度</text>
          <picker :range="portabilityLabels" @change="onPortabilityChange">
            <view class="picker-box">{{ optionLabel(portabilities, form.portability) || '请选择便携度' }}</view>
          </picker>
        </view>
      </view>

      <view class="field">
        <view class="label-row">
          <text class="label">地区</text>
          <text class="location-action" @click="syncRegionFromStore">使用我的地区</text>
        </view>
        <view class="region-row">
          <text class="region-chip">{{ form.province || '未设置省份' }}</text>
          <text class="region-chip">{{ form.city || '未设置城市' }}</text>
        </view>
      </view>

      <view class="field">
        <text class="label">风味标签（最多4个）</text>
        <view class="tag-input-row" v-if="tags.length < 4">
          <input
            v-model="tagInput"
            class="input"
            placeholder="例如：麻辣、果香、手工"
            @confirm="addTag"
          />
          <button size="mini" class="tag-btn" @click="addTag">添加</button>
        </view>
        <view class="tag-list">
          <view class="tag" v-for="(tag, idx) in tags" :key="idx" @click="removeTag(idx)">
            {{ tag }} ×
          </view>
        </view>
      </view>

      <view class="field">
        <text class="label">描述</text>
        <textarea
          v-model="form.description"
          class="textarea"
          placeholder="介绍这份特产的口味、做法和交换偏好"
        />
      </view>

      <button class="submit" :loading="submitting" @click="submit">发布特产</button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import request, { uploadWithAuth } from '@/utils/request'
import { useUserStore } from '@/stores/user'
import { ensureAuthed } from '@/utils/auth'
import { parseUploadResponse, resolveUploadUrl } from '@/utils/upload-response.js'

const userStore = useUserStore()
const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL || 'http://127.0.0.1:8001/django/api/v1'

const categories = ref<any[]>([])
const seasons = ref<any[]>([])
const shelfLives = ref<any[]>([])
const portabilities = ref<any[]>([])
const submitting = ref(false)

const form = reactive({
  title: '',
  category: '',
  season: '',
  shelf_life: '',
  portability: '',
  description: '',
  images: [] as string[],
  initial_tags: [] as string[],
  province: '',
  city: '',
  region_code: ''
})

const tags = ref<string[]>([])
const tagInput = ref('')

const categoryLabels = computed(() => categories.value.map((x: any) => x.label))
const seasonLabels = computed(() => seasons.value.map((x: any) => x.label))
const shelfLifeLabels = computed(() => shelfLives.value.map((x: any) => x.label))
const portabilityLabels = computed(() => portabilities.value.map((x: any) => x.label))

const optionLabel = (list: any[], value: string) => {
  const item = list.find((x: any) => x.value === value)
  return item?.label || ''
}

const syncRegionFromStore = () => {
  form.region_code = userStore.userInfo.region_code || ''
  form.province = userStore.userInfo.province || ''
  form.city = userStore.userInfo.city || ''
}

const loadOptions = async () => {
  try {
    const options: any = await request.get('/options/')
    categories.value = options.filter((o: any) => o.type === 'Category')
    seasons.value = options.filter((o: any) => o.type === 'Season')
    shelfLives.value = options.filter((o: any) => o.type === 'ShelfLife')
    portabilities.value = options.filter((o: any) => o.type === 'Portability')

    if (!form.category && categories.value.length) form.category = categories.value[0].value
    if (!form.season && seasons.value.length) form.season = seasons.value[0].value
    if (!form.shelf_life && shelfLives.value.length) form.shelf_life = shelfLives.value[0].value
    if (!form.portability && portabilities.value.length) form.portability = portabilities.value[0].value
  } catch (e) {
    console.error('load options failed', e)
  }
}

onShow(async () => {
  if (!ensureAuthed({ toast: '请先登录后发布', redirect: '/pages/publish/publish' })) return
  if (!userStore.userInfo.id) {
    try {
      await userStore.fetchUserInfo()
    } catch (e) {
      console.error('fetch user failed', e)
    }
  }
  syncRegionFromStore()
  await loadOptions()
})

const onCategoryChange = (e: any) => {
  const idx = Number(e.detail.value)
  if (categories.value[idx]) form.category = categories.value[idx].value
}

const onSeasonChange = (e: any) => {
  const idx = Number(e.detail.value)
  if (seasons.value[idx]) form.season = seasons.value[idx].value
}

const onShelfLifeChange = (e: any) => {
  const idx = Number(e.detail.value)
  if (shelfLives.value[idx]) form.shelf_life = shelfLives.value[idx].value
}

const onPortabilityChange = (e: any) => {
  const idx = Number(e.detail.value)
  if (portabilities.value[idx]) form.portability = portabilities.value[idx].value
}

const addTag = () => {
  const value = tagInput.value.trim()
  if (!value) return
  if (tags.value.length >= 4) {
    uni.showToast({ title: '最多 4 个标签', icon: 'none' })
    return
  }
  if (!tags.value.includes(value)) tags.value.push(value)
  tagInput.value = ''
}

const removeTag = (index: number) => {
  tags.value.splice(index, 1)
}

const chooseImage = () => {
  if (!ensureAuthed({ toast: '请先登录后上传图片', redirect: '/pages/publish/publish' })) return
  uni.chooseImage({
    count: 3 - form.images.length,
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
      const uploadRes: any = await uploadWithAuth({
        url: `${API_BASE}/upload/`,
        filePath: path,
        name: 'file'
      })
      form.images.push(resolveUploadUrl(API_BASE, parseUploadResponse(uploadRes)))
    } catch (e) {
      console.error('upload image failed', e)
      uni.showToast({ title: '图片上传失败', icon: 'none' })
    }
  }
  uni.hideLoading()
}

const removeImage = (index: number) => {
  form.images.splice(index, 1)
}

const submit = async () => {
  if (!ensureAuthed({ toast: '请先登录后发布', redirect: '/pages/publish/publish' })) return
  if (!form.title.trim()) {
    uni.showToast({ title: '请输入名称', icon: 'none' })
    return
  }
  if (!form.images.length) {
    uni.showToast({ title: '请至少上传一张图片', icon: 'none' })
    return
  }
  if (!form.region_code) {
    uni.showToast({ title: '请先完善地区信息', icon: 'none' })
    return
  }

  submitting.value = true
  form.initial_tags = [...tags.value]
  try {
    await request.authPost('/items/', form)
    uni.showToast({ title: '发布成功', icon: 'success' })
    setTimeout(() => uni.switchTab({ url: '/pages/index/index' }), 350)
  } catch (e) {
    console.error('create item failed', e)
  } finally {
    submitting.value = false
  }
}
</script>

<style>
.page {
  min-height: 100vh;
  background: #f8fafc;
}

.topbar {
  padding: 26rpx 28rpx 14rpx;
  background: #fff;
  border-bottom: 1rpx solid #e2e8f0;
}

.topbar-title {
  display: block;
  font-size: 36rpx;
  font-weight: 800;
  color: #0f172a;
}

.topbar-sub {
  display: block;
  margin-top: 4rpx;
  font-size: 22rpx;
  color: #64748b;
}

.panel {
  padding: 22rpx;
}

.field {
  background: #fff;
  border: 1rpx solid #e2e8f0;
  border-radius: 20rpx;
  padding: 20rpx;
  margin-bottom: 16rpx;
}

.card-field {
  margin-bottom: 0;
}

.label {
  display: block;
  margin-bottom: 12rpx;
  color: #334155;
  font-size: 24rpx;
  font-weight: 600;
}

.label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12rpx;
}

.location-action {
  color: #ea580c;
  font-size: 22rpx;
}

.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14rpx;
  margin-bottom: 16rpx;
}

.input {
  width: 100%;
  height: 78rpx;
  border-radius: 14rpx;
  background: #f8fafc;
  border: 1rpx solid #e2e8f0;
  padding: 0 18rpx;
  box-sizing: border-box;
  font-size: 26rpx;
  color: #0f172a;
}

.picker-box {
  height: 78rpx;
  border-radius: 14rpx;
  background: #f8fafc;
  border: 1rpx solid #e2e8f0;
  display: flex;
  align-items: center;
  padding: 0 18rpx;
  font-size: 24rpx;
  color: #334155;
}

.region-row {
  display: flex;
  gap: 10rpx;
}

.region-chip {
  padding: 8rpx 14rpx;
  border-radius: 999rpx;
  background: #f1f5f9;
  color: #475569;
  font-size: 22rpx;
}

.image-area {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}

.image-item,
.upload-slot {
  width: 200rpx;
  height: 140rpx;
  border-radius: 14rpx;
  overflow: hidden;
  position: relative;
}

.image-item {
  border: 1rpx solid #e2e8f0;
}

.image {
  width: 100%;
  height: 100%;
  background: #e2e8f0;
}

.remove {
  position: absolute;
  right: 8rpx;
  top: 8rpx;
  width: 34rpx;
  height: 34rpx;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
  text-align: center;
  line-height: 34rpx;
  font-size: 24rpx;
}

.upload-slot {
  border: 1rpx dashed #cbd5e1;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.upload-plus {
  font-size: 44rpx;
  color: #94a3b8;
  line-height: 1;
}

.upload-tip {
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #64748b;
}

.tag-input-row {
  display: flex;
  gap: 10rpx;
  align-items: center;
}

.tag-btn {
  background: #ea580c;
  color: #fff;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
  margin-top: 12rpx;
}

.tag {
  padding: 8rpx 14rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
  color: #9a3412;
  background: #ffedd5;
  border: 1rpx solid #fed7aa;
}

.textarea {
  width: 100%;
  min-height: 180rpx;
  border-radius: 14rpx;
  background: #f8fafc;
  border: 1rpx solid #e2e8f0;
  padding: 16rpx;
  box-sizing: border-box;
  font-size: 26rpx;
  color: #0f172a;
}

.submit {
  margin-top: 8rpx;
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 16rpx;
  border: none;
  background: #0f172a;
  color: #fff;
  font-size: 30rpx;
  font-weight: 700;
}
</style>
