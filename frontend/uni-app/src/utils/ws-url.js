export const getWebSocketRoot = (apiBase) => {
  const apiUrl = new URL(apiBase)
  apiUrl.protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'
  apiUrl.pathname = ''
  apiUrl.search = ''
  apiUrl.hash = ''
  return apiUrl.toString().replace(/\/$/, '')
}

export const getChatWebSocketUrl = (apiBase, conversationId) =>
  `${getWebSocketRoot(apiBase)}/ws/chat/conversations/${conversationId}/`
