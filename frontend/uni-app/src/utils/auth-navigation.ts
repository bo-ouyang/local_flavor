const TAB_PAGES = new Set([
  '/pages/index/index',
  '/pages/stats/map',
  '/pages/publish/publish',
  '/pages/profile/profile'
])

const normalizePath = (url: string) => {
  if (!url) return '/pages/index/index'
  return url.split('?')[0]
}

export const isTabPage = (url: string) => TAB_PAGES.has(normalizePath(url))

export const getCurrentPageUrl = () => {
  const pages = getCurrentPages()
  if (!pages.length) return '/pages/index/index'
  const current: any = pages[pages.length - 1]
  const route = `/${current.route || 'pages/index/index'}`
  const opts = current.options || {}
  const query = Object.keys(opts)
    .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(opts[key])}`)
    .join('&')
  return query ? `${route}?${query}` : route
}

export const goLogin = (redirect?: string) => {
  const pages = getCurrentPages()
  const currentRoute = pages.length ? pages[pages.length - 1].route : ''
  if (currentRoute === 'pages/auth/login') return

  const target = redirect || getCurrentPageUrl()
  const loginUrl = `/pages/auth/login?redirect=${encodeURIComponent(target)}`
  if (pages.length >= 9) {
    uni.redirectTo({ url: loginUrl })
    return
  }
  uni.navigateTo({ url: loginUrl })
}
