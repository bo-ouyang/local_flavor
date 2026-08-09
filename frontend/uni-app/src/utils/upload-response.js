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

export const resolveUploadUrl = (apiBase, uploadUrl) => {
  let apiUrl
  try {
    apiUrl = new URL(apiBase)
  } catch (_) {
    throw new Error('invalid API base')
  }
  if (!/^https?:$/.test(apiUrl.protocol)) throw new Error('invalid API base')
  const resolved = new URL(uploadUrl, `${apiUrl.origin}/`)
  if (resolved.origin !== apiUrl.origin || !resolved.pathname.startsWith('/static/')) {
    throw new Error('invalid upload URL')
  }
  return resolved.toString()
}
