import { defineStore } from 'pinia'
import request from '@/utils/request'
import { clearLocalAuth, getAccessToken, saveLoginResult } from '@/utils/request'

export const useUserStore = defineStore('user', {
	state: () => ({
		userInfo: uni.getStorageSync('user_info') || {
            id: 0,
            nickname: 'Guest',
            region: '',
            region_code: '',
            province: '',
            city: '',
            latitude: null as number | null,
            longitude: null as number | null
        },
        token: getAccessToken()
	}),
	actions: {
        clearLocalAuth() {
            this.token = ''
            this.userInfo = {
                id: 0,
                nickname: 'Guest',
                region: '',
                region_code: '',
                province: '',
                city: '',
                latitude: null,
                longitude: null
            }
            clearLocalAuth()
        },
        syncAccessToken(accessToken?: string) {
            this.token = accessToken || getAccessToken()
        },
        async logout() {
            try {
                await request.logout()
            } finally {
                this.clearLocalAuth()
            }
        },

        applyLoginResult(res: any) {
            const session = saveLoginResult(res)
            this.syncAccessToken(session?.access_token)
            if (res.user) {
                this.setUserInfo(res.user)
            }
            return this.token
        },

        async loginWithWechat() {
            if (this.token) return this.token
            const loginRes = await uni.login({ provider: 'weixin' })
            const code = loginRes?.code
            if (!code) {
                throw new Error('wechat login failed: no code')
            }
            const res: any = await request.post('/user/wx-login', { code })
            return this.applyLoginResult(res)
        },

        async loginWithPhone(phone: string, password: string) {
            const res: any = await request.post('/user/phone-login', { phone, password })
            return this.applyLoginResult(res)
        },

        async loginWithTestAccount() {
            return this.loginWithPhone('13800000000', 'Test@123456')
        },

        async ensureLoginAndProfile() {
            if (!this.token) return false
            await this.fetchUserInfo()
            return true
        },

        setUserInfo(info: any) {
            const region = info.city && info.province ? `${info.city}, ${info.province}` : (this.userInfo.region || '')
            this.userInfo = { ...this.userInfo, ...info, region }
            uni.setStorageSync('user_info', this.userInfo)
        },
		async updateRegion(data: { province: string, city: string, region_code?: string }) {
            try {
                const res: any = await request.authPut('/user/region', data)
                this.setUserInfo(res)
                return res
            } catch (error) {
                throw error
            }
		},
        async updateRegionByCoords(
            data: { latitude: number; longitude: number },
            opts?: { skipToast?: boolean }
        ) {
            try {
                const res: any = await request.authPut(
                    '/user/region',
                    data,
                    { skipToast: !!opts?.skipToast }
                )
                this.setUserInfo(res)
                return res
            } catch (error) {
                throw error
            }
        },
        async fetchUserInfo() {
            try {
                const res: any = await request.authGet('/user/me')
                this.setUserInfo(res)
                return res
            } catch (error) {
                console.error('Fetch user info failed', error)
                throw error
            }
        }
	}
})
