<script>
	import { useUserStore } from '@/stores/user'

	export default {
		onLaunch: async function() {
			console.log('App Launch')
			const userStore = useUserStore()
            if (!userStore.token) return
            try {
			    await userStore.fetchUserInfo()
            } catch (e) {
                console.error('init profile failed', e)
                userStore.logout()
            }
		},
		onShow: function() {
			console.log('App Show')
		},
		onHide: function() {
			console.log('App Hide')
		}
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
