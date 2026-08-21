import { defineStore } from 'pinia'
import request from '@/utils/request'
import { authSession, clearAuthSession, setAuthSession, subscribeToAuthSession } from '@/utils/session'

const defaultUserInfo = () => ({
    id: 0,
    nickname: 'Guest',
    region: '',
    region_code: '',
    province: '',
    city: '',
    latitude: null as number | null,
    longitude: null as number | null
})

const useUserStoreBase = defineStore('user', {
	state: () => ({
		userInfo: uni.getStorageSync('user_info') || defaultUserInfo()
	}),
	getters: {
        token: () => authSession.accessToken,
        refreshToken: () => authSession.refreshToken,
        sessionId: () => authSession.sessionId
    },
	actions: {
        resetUserInfo() {
            this.userInfo = defaultUserInfo()
            uni.removeStorageSync('user_info')
        },
        async logout() {
            if (this.token) {
                try {
                    await request.post('/user/session/logout', undefined, {
                        authMode: 'required',
                        skipToast: true
                    })
                } catch (error) {
                    console.warn('Server logout failed', error)
                }
            }
            clearAuthSession()
            this.resetUserInfo()
        },

        applyLoginResult(res: any) {
            const session = res.session || res
            setAuthSession({
                access_token: session.access_token || res.access_token || '',
                refresh_token: session.refresh_token || res.refresh_token || '',
                session_id: session.session_id ?? res.session_id,
                access_expires_at: session.access_expires_at,
                refresh_expires_at: session.refresh_expires_at
            })
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

const storesBoundToSession = new WeakSet<object>()

export const useUserStore = () => {
    const store = useUserStoreBase()
    if (!storesBoundToSession.has(store)) {
        storesBoundToSession.add(store)
        subscribeToAuthSession((accessToken) => {
            if (!accessToken) store.resetUserInfo()
        })
    }
    return store
}
