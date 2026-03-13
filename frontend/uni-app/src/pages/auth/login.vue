<template>
  <view class="login-page">
    <view class="hero">
      <text class="title">特产交换</text>
      <text class="sub">登录后可发布、交换和聊天</text>
    </view>

    <view class="panel">
      <view class="switcher">
        <view class="tab" :class="{ active: mode === 'wechat' }" @click="mode = 'wechat'">微信授权</view>
        <view class="tab" :class="{ active: mode === 'phone' }" @click="mode = 'phone'">手机号</view>
      </view>

      <view v-if="mode === 'wechat'" class="wechat-area">
        <button type="primary" class="btn" :loading="loading" @click="loginWechat">微信一键登录</button>
      </view>

      <view v-else class="phone-area">
        <input v-model="phone" class="input" type="number" maxlength="11" placeholder="请输入手机号" />
        <input v-model="password" class="input" password placeholder="请输入密码" />
        <button type="primary" class="btn" :loading="loading" @click="loginPhone">手机号登录</button>

        <view class="demo-box">
          <text class="demo-title">测试账号（点击自动填充）</text>
          <view class="demo-list">
            <view v-for="acc in testAccounts" :key="acc.phone" class="demo-item" @click="fillDemo(acc)">
              <text>{{ acc.nickname }}</text>
              <text>{{ acc.phone }}</text>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onBackPress, onLoad, onShow } from '@dcloudio/uni-app'
import { useUserStore } from '@/stores/user'
import { isTabPage } from '@/utils/auth'

const userStore = useUserStore()
const mode = ref<'wechat' | 'phone'>('wechat')
const loading = ref(false)
const phone = ref('')
const password = ref('')
const redirectUrl = ref('/pages/profile/profile')

const testAccounts = [
  { nickname: 'Demo_Alice', phone: '13800000000', password: 'Test@123456' },
  { nickname: 'Demo_Bob', phone: '13800000001', password: 'Test@123456' },
  { nickname: 'Demo_Carol', phone: '13800000002', password: 'Test@123456' },
  { nickname: 'Demo_David', phone: '13800000003', password: 'Test@123456' }
]

const normalizedTarget = () => {
  let target = (redirectUrl.value || '').trim()
  if (!target || target.startsWith('/pages/auth/login')) {
    target = '/pages/profile/profile'
  }
  return target
}

const navigateAfterLogin = () => {
  const target = normalizedTarget()
  const targetPath = target.split('?')[0]

  if (isTabPage(target)) {
    uni.switchTab({
      url: targetPath,
      fail: () => {
        uni.reLaunch({ url: '/pages/profile/profile' })
      }
    })
    return
  }

  uni.reLaunch({
    url: target,
    fail: () => {
      uni.switchTab({ url: '/pages/profile/profile' })
    }
  })
}

const fillDemo = (acc: any) => {
  mode.value = 'phone'
  phone.value = acc.phone
  password.value = acc.password
}

const syncLocationOnFirstLogin = async () => {
  const hasRegion = !!(userStore.userInfo?.province && userStore.userInfo?.city)
  if (hasRegion) return
  try {
    const locRes: any = await uni.getLocation({ type: 'gcj02' })
    const latitude = Number(locRes?.latitude)
    const longitude = Number(locRes?.longitude)
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return
    await userStore.updateRegionByCoords({ latitude, longitude }, { skipToast: true })
  } catch (e) {
    // 允许用户拒绝定位，不影响登录
    console.warn('sync location skipped', e)
  }
}

const loginWechat = async () => {
  if (loading.value) return
  loading.value = true
  try {
    await userStore.loginWithWechat()
    await userStore.fetchUserInfo()
    await syncLocationOnFirstLogin()
    uni.showToast({ title: '登录成功', icon: 'success' })
    setTimeout(navigateAfterLogin, 250)
  } catch (e) {
    console.error('wechat login failed', e)
    uni.showToast({ title: '微信登录失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

const loginPhone = async () => {
  if (loading.value) return
  if (!/^1\d{10}$/.test(phone.value)) {
    uni.showToast({ title: '手机号格式不正确', icon: 'none' })
    return
  }
  if (!password.value || password.value.length < 6) {
    uni.showToast({ title: '密码至少6位', icon: 'none' })
    return
  }

  loading.value = true
  try {
    await userStore.loginWithPhone(phone.value, password.value)
    await userStore.fetchUserInfo()
    await syncLocationOnFirstLogin()
    uni.showToast({ title: '登录成功', icon: 'success' })
    setTimeout(navigateAfterLogin, 250)
  } catch (e) {
    console.error('phone login failed', e)
    uni.showToast({ title: '手机号或密码错误', icon: 'none' })
  } finally {
    loading.value = false
  }
}

onLoad((options: any) => {
  if (!options?.redirect) return
  try {
    redirectUrl.value = decodeURIComponent(options.redirect)
  } catch {
    redirectUrl.value = options.redirect
  }
})

onShow(async () => {
  if (!userStore.token) return
  try {
    await userStore.fetchUserInfo()
    navigateAfterLogin()
  } catch {
    userStore.logout()
  }
})

onBackPress(() => {
  const pages = getCurrentPages()
  if (pages.length > 1) return false
  const target = normalizedTarget()
  const targetPath = target.split('?')[0]
  if (isTabPage(target)) {
    uni.switchTab({ url: targetPath })
    return true
  }
  uni.reLaunch({ url: '/pages/profile/profile' })
  return true
})
</script>

<style>
.login-page { min-height: 100vh; padding: 40rpx; background: linear-gradient(180deg, #fff2e8 0%, #fff 45%); }
.hero { margin-top: 80rpx; margin-bottom: 40rpx; }
.title { font-size: 56rpx; font-weight: 800; color: #222; display: block; }
.sub { margin-top: 12rpx; font-size: 26rpx; color: #666; display: block; }

.panel { background: #fff; border-radius: 24rpx; padding: 28rpx; box-shadow: 0 12rpx 40rpx rgba(0, 0, 0, 0.08); }
.switcher { display: flex; background: #f5f5f5; border-radius: 999rpx; padding: 8rpx; margin-bottom: 26rpx; }
.tab { flex: 1; text-align: center; padding: 14rpx 0; border-radius: 999rpx; color: #666; }
.tab.active { background: #ff6a00; color: #fff; font-weight: 700; }

.input { height: 84rpx; border: 1rpx solid #e5e5e5; border-radius: 14rpx; padding: 0 20rpx; margin-bottom: 18rpx; }
.btn { margin-top: 8rpx; border-radius: 999rpx; background: #ff6a00; }

.demo-box { margin-top: 26rpx; border-top: 1rpx dashed #eee; padding-top: 18rpx; }
.demo-title { font-size: 24rpx; color: #888; display: block; margin-bottom: 10rpx; }
.demo-list { display: flex; flex-direction: column; gap: 10rpx; }
.demo-item { display: flex; justify-content: space-between; align-items: center; padding: 14rpx 18rpx; background: #fafafa; border-radius: 12rpx; color: #333; font-size: 24rpx; }
</style>
