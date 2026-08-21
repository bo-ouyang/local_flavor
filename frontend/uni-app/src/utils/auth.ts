import { useUserStore } from '@/stores/user'
import { goLogin } from '@/utils/auth-navigation'

export { getCurrentPageUrl, goLogin, isTabPage } from '@/utils/auth-navigation'

export const ensureAuthed = (opts?: { redirect?: string; toast?: string }) => {
  const userStore = useUserStore()
  if (userStore.token) return true
  if (opts?.toast) {
    uni.showToast({ title: opts.toast, icon: 'none' })
  }
  goLogin(opts?.redirect)
  return false
}
