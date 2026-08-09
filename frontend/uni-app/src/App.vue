<script>
	import { useUserStore } from '@/stores/user'
	import { onSessionRefreshed, setAuthFailureHandler } from '@/utils/request'
	import { goLogin } from '@/utils/auth'

	export default {
		onLaunch: async function() {
			const userStore = useUserStore()
			setAuthFailureHandler(() => {
				userStore.clearLocalAuth()
				goLogin()
			})
			onSessionRefreshed((session) => userStore.syncAccessToken(session.access_token))
            if (!userStore.token) return
            try {
			    await userStore.fetchUserInfo()
            } catch (e) {
                console.error('init profile failed', e)
                userStore.clearLocalAuth()
            }
		},
		onShow: function() {},
		onHide: function() {}
	}
</script>

<style>
	/* Global Styles */
    body {
        background-color: #f8f8f8;
        font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Helvetica, Segoe UI, Arial, Roboto, 'PingFang SC', 'miui', 'Hiragino Sans GB', 'Microsoft Yahei', sans-serif;
    }
    view {
        box-sizing: border-box;
    }
</style>
