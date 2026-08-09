export const parseUploadResponse = (response) => {
  let payload
  try {
    payload = typeof response?.data === 'string' ? JSON.parse(response.data) : response?.data
  } catch (_) {
    throw new Error('upload failed')
  }
  const url = payload?.code === 0 ? payload?.data?.url : ''
  if (typeof url !== 'string' || !url) throw new Error('upload failed')
  return url
}

const getBrowserOrigin = () => {
  try {
    return typeof globalThis.location?.origin === 'string' ? globalThis.location.origin : ''
  } catch (_) {
    return ''
  }
}

const parseHttpUrl = (value) => {
  const url = new URL(value)
  if (!/^https?:$/.test(url.protocol)) throw new Error('invalid URL')
  return url
}

export const resolveUploadUrl = (apiBase, uploadUrl, browserOrigin) => {
  let apiUrl
  try {
    const isRootRelative = typeof apiBase === 'string' && /^\/(?!\/)/.test(apiBase)
    apiUrl = isRootRelative
      ? new URL(apiBase, parseHttpUrl(browserOrigin === undefined ? getBrowserOrigin() : browserOrigin))
      : parseHttpUrl(apiBase)
  } catch (_) {
    throw new Error(typeof apiBase === 'string' && /^\/(?!\/)/.test(apiBase) ? 'upload failed' : 'invalid API base')
  }
  const resolved = new URL(uploadUrl, `${apiUrl.origin}/`)
  if (resolved.origin !== apiUrl.origin || !resolved.pathname.startsWith('/static/')) {
    throw new Error('invalid upload URL')
  }
  return resolved.toString()
}
