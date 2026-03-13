<template>
  <view class="page">
    <view class="header-wrap">
      <view class="header-top">
        <text class="brand">LocalTreasure</text>
        <view class="filter-btn">今日上新</view>
      </view>

      <view class="search-box">
        <input
          v-model="searchTerm"
          class="search-input"
          placeholder="搜索今日上新的特产 / 地点 / 风味标签"
          confirm-type="search"
        />
      </view>

      <scroll-view scroll-x class="category-scroll">
        <view
          class="category-chip"
          :class="{ active: currentCategory === '' }"
          @click="setCategory('')"
        >
          全部
        </view>
        <view
          v-for="cat in categories"
          :key="cat"
          class="category-chip"
          :class="{ active: currentCategory === cat }"
          @click="setCategory(cat)"
        >
          {{ categoryMap[cat] || cat }}
        </view>
      </scroll-view>
    </view>

    <view class="product-list">
      <view class="product-card" v-for="item in filteredItems" :key="item.id" @click="goDetail(item.id)">
        <view class="product-cover-wrap">
          <image :src="getCover(item)" mode="aspectFill" class="product-cover" />
          <text class="product-tag">{{ categoryMap[item.category] || item.category || '其他' }}</text>
        </view>
        <view class="product-body">
          <view class="product-top">
            <text class="product-title">{{ item.title || '未命名特产' }}</text>
            <text class="product-season">{{ seasonMap[item.season] || item.season || '-' }}</text>
          </view>
          <text class="product-meta">{{ item.city || item.province || '未知地区' }}</text>
          <text class="product-desc">{{ item.description || '暂无描述' }}</text>
        </view>
      </view>

      <view v-if="!loading && filteredItems.length === 0" class="empty">
        今日暂无上新，稍后再来看看
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import request from '@/utils/request'

const loading = ref(false)
const items = ref<any[]>([])
const categories = ref<string[]>([])
const currentCategory = ref('')
const searchTerm = ref('')

const categoryMap = ref<Record<string, string>>({})
const seasonMap = ref<Record<string, string>>({
  Spring: '春',
  Summer: '夏',
  Autumn: '秋',
  Winter: '冬',
  AllYear: '四季',
})
const fallbackCover = 'https://dummyimage.com/400x300/f1f5f9/94a3b8&text=Local+Treasure'

const filteredItems = computed(() => {
  const keyword = searchTerm.value.trim().toLowerCase()
  return items.value.filter((item: any) => {
    const matchedCategory = !currentCategory.value || item.category === currentCategory.value
    const title = String(item?.title || '').toLowerCase()
    const city = String(item?.city || '').toLowerCase()
    const province = String(item?.province || '').toLowerCase()
    const flavorText = Array.isArray(item?.flavor_tags)
      ? item.flavor_tags.map((x: any) => String(x?.tag_name || '')).join(' ')
      : ''
    const matchedSearch =
      !keyword ||
      title.includes(keyword) ||
      city.includes(keyword) ||
      province.includes(keyword) ||
      flavorText.toLowerCase().includes(keyword)
    return matchedCategory && matchedSearch
  })
})

const normalizeItems = (payload: any): any[] => {
  const raw = Array.isArray(payload) ? payload : []
  return raw.map((item: any) => ({
    ...item,
    images: Array.isArray(item?.images) ? item.images : (item?.images ? [item.images] : [])
  }))
}

const flattenTodayByRegion = (groups: any[]): any[] => {
  const list: any[] = []
  groups.forEach((g: any) => {
    ;(g.items || []).forEach((it: any) => {
      list.push({
        ...it,
        region_code: it.region_code || g.region_code,
        province: it.province || g.province,
        city: it.city || g.city
      })
    })
  })
  return list
}

const getCover = (item: any) => item?.images?.[0] || fallbackCover

const setCategory = (cat: string) => {
  currentCategory.value = cat
}

const loadOptions = async () => {
  try {
    const [categoryOpts, seasonOpts] = await Promise.all([
      request.get('/options/', { type: 'Category' }),
      request.get('/options/', { type: 'Season' })
    ]) as any

    categories.value = (categoryOpts || []).map((it: any) => it.value)
    const nextCategoryMap: Record<string, string> = {}
    ;(categoryOpts || []).forEach((it: any) => {
      nextCategoryMap[it.value] = it.label
    })
    categoryMap.value = nextCategoryMap

    const nextSeasonMap = { ...seasonMap.value }
    ;(seasonOpts || []).forEach((it: any) => {
      nextSeasonMap[it.value] = it.label
    })
    seasonMap.value = nextSeasonMap

    if (currentCategory.value && !categories.value.includes(currentCategory.value)) {
      currentCategory.value = ''
    }
  } catch (e) {
    console.error('load options failed', e)
  }
}

const loadItems = async (isRefresh = false) => {
  loading.value = true
  try {
    const res: any = await request.get('/items/today-by-region', { region_limit: 20, item_limit: 20 })
    const merged = flattenTodayByRegion(Array.isArray(res) ? res : [])
    items.value = normalizeItems(merged)
  } catch (e) {
    console.error('load today items failed', e)
  } finally {
    loading.value = false
    if (isRefresh) uni.stopPullDownRefresh()
  }
}

const goDetail = (id: number) => {
  uni.navigateTo({ url: `/pages/detail/detail?id=${id}` })
}

onPullDownRefresh(async () => {
  await loadItems(true)
})

onShow(async () => {
  await Promise.all([loadOptions(), loadItems()])
})
</script>

<style>
.page {
  min-height: 100vh;
  background: #f8fafc;
  padding-bottom: 32rpx;
}

.header-wrap {
  position: sticky;
  top: 0;
  z-index: 20;
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
  margin-bottom: 18rpx;
}

.search-input {
  height: 72rpx;
  font-size: 26rpx;
  color: #0f172a;
}

.category-scroll {
  white-space: nowrap;
}

.category-chip {
  display: inline-block;
  padding: 12rpx 24rpx;
  border-radius: 999rpx;
  border: 1rpx solid #e2e8f0;
  background: #fff;
  color: #475569;
  font-size: 22rpx;
  margin-right: 12rpx;
}

.category-chip.active {
  background: #0f172a;
  border-color: #0f172a;
  color: #fff;
}

.product-list {
  padding: 10rpx 24rpx 30rpx;
}

.product-card {
  margin-bottom: 16rpx;
  border-radius: 22rpx;
  overflow: hidden;
  border: 1rpx solid #e2e8f0;
  background: #fff;
  box-shadow: 0 8rpx 24rpx rgba(15, 23, 42, 0.06);
}

.product-cover-wrap {
  position: relative;
}

.product-cover {
  width: 100%;
  height: 340rpx;
  background: #e2e8f0;
}

.product-tag {
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

.product-body {
  padding: 18rpx;
}

.product-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14rpx;
}

.product-title {
  flex: 1;
  font-size: 30rpx;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.35;
}

.product-season {
  font-size: 20rpx;
  color: #b45309;
  background: #fffbeb;
  border: 1rpx solid #fde68a;
  border-radius: 999rpx;
  padding: 4rpx 10rpx;
}

.product-meta {
  display: block;
  margin-top: 8rpx;
  color: #64748b;
  font-size: 22rpx;
}

.product-desc {
  display: block;
  margin-top: 10rpx;
  color: #475569;
  font-size: 24rpx;
  line-height: 1.5;
}

.empty {
  margin-top: 80rpx;
  text-align: center;
  color: #94a3b8;
  font-size: 24rpx;
}
</style>
