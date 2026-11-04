const API_BASE = '/api'

function csrfCookie() {
  return document.cookie.split('; ').find((item) => item.startsWith('csrftoken='))?.split('=')[1] || ''
}

/**
 * 查询 Django JSON API 的分页集合。
 * 页面只消费 data.items，避免把后端响应结构散落在组件中。
 */
export async function fetchCollection(path, params = {}) {
  const query = new URLSearchParams({ limit: '100', ...params })
  const response = await fetch(`${API_BASE}${path}?${query.toString()}`, {
    headers: { Accept: 'application/json' },
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok || body.success === false) {
    throw new Error(body?.error?.message || `接口请求失败（${response.status}）`)
  }
  return body.data || { items: [], count: 0 }
}

/** 上传一张图像并调用 FloodNet 语义分割模型。 */
export async function recognizeImage(file, modelArtifactId = '') {
  if (!csrfCookie()) {
    await fetch(`${API_BASE}/csrf/`, { headers: { Accept: 'application/json' } })
  }
  const form = new FormData()
  form.append('image', file)
  if (modelArtifactId) form.append('model_artifact_id', modelArtifactId)
  const response = await fetch(`${API_BASE}/vision/infer/`, {
    method: 'POST',
    body: form,
    headers: {
      Accept: 'application/json',
      ...(csrfCookie() ? { 'X-CSRFToken': csrfCookie() } : {}),
    },
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok || body.success === false) {
    throw new Error(body?.error?.message || `模型接口请求失败（${response.status}）`)
  }
  return body.data || {}
}

