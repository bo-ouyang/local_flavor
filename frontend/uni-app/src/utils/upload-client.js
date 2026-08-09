const uploadError = (result) => ({
  code: result.statusCode,
  message: `HTTP ${result.statusCode}`
})

export const createUploadClient = ({ getAccessToken, refresh, upload }) => {
  let refreshPromise = null

  const refreshOnce = () => {
    if (!refreshPromise) {
      refreshPromise = Promise.resolve(refresh()).finally(() => { refreshPromise = null })
    }
    return refreshPromise
  }

  const send = async (options, retried = false) => {
    const accessToken = getAccessToken()
    let result
    try {
      result = await upload({
        ...options,
        header: {
          ...options.header,
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {})
        }
      })
    } catch (_) {
      throw { code: 0, message: 'Upload failed' }
    }
    if (result.statusCode !== 401) {
      if (result.statusCode >= 200 && result.statusCode < 300) return result
      throw uploadError(result)
    }
    if (retried) throw uploadError(result)
    if (accessToken && accessToken !== getAccessToken()) return send(options, true)
    await refreshOnce()
    return send(options, true)
  }

  return { upload: (options) => send(options) }
}
