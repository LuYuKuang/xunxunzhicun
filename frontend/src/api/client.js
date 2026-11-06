const API_BASE = '/api'

function csrfCookie() {
  return document.cookie.split('; ').find((item) => item.startsWith('csrftoken='))?.split('=')[1] || ''
}

async function parseResponse(response, fallbackMessage) {
  const body = await response.json().catch(() => ({}))
  if (!response.ok || body.success === false) {
    throw new Error(body?.error?.message || `${fallbackMessage}（${response.status}）`)
  }
  return body.data
}

async function ensureCsrf() {
  if (!csrfCookie()) {
    await fetch(`${API_BASE}/csrf/`, { headers: { Accept: 'application/json' } })
  }
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
  return (await parseResponse(response, '接口请求失败')) || { items: [], count: 0 }
}

/** 查询单条资源，保持 Django 的 {success, data, error} 响应格式。 */
export async function fetchResource(path) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: 'application/json' },
  })
  return parseResponse(response, '资源读取失败')
}

/** 上传原图并创建或更新一个 Mission。 */
export async function uploadImage(file, missionId = '', name = '') {
  await ensureCsrf()
  const form = new FormData()
  form.append('image', file)
  if (missionId) form.append('mission_id', missionId)
  if (name) form.append('name', name)
  const response = await fetch(`${API_BASE}/images/upload/`, {
    method: 'POST',
    body: form,
    headers: {
      Accept: 'application/json',
      ...(csrfCookie() ? { 'X-CSRFToken': csrfCookie() } : {}),
    },
  })
  return parseResponse(response, '图片上传失败')
}

/** 更新复查任务，使用后端约定的 PATCH + JSON。 */
export async function updateMission(missionId, payload) {
  await ensureCsrf()
  const response = await fetch(`${API_BASE}/missions/${missionId}/`, {
    method: 'PATCH',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(csrfCookie() ? { 'X-CSRFToken': csrfCookie() } : {}),
    },
    body: JSON.stringify(payload),
  })
  return parseResponse(response, '任务更新失败')
}

/** 读取灾情类别目录。 */
export async function fetchDisasterCategories() {
  const response = await fetch(`${API_BASE}/disaster-categories/`, {
    headers: { Accept: 'application/json' },
  })
  return parseResponse(response, '灾情类别读取失败')
}

/** 读取后端健康状态。 */
export async function fetchHealth() {
  const response = await fetch(`${API_BASE}/health/`, {
    headers: { Accept: 'application/json' },
  })
  return parseResponse(response, '服务状态读取失败')
}

/** 创建一次调度仿真运行记录。 */
export async function createSimulationRun(payload) {
  await ensureCsrf()
  const response = await fetch(`${API_BASE}/simulation-runs/`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(csrfCookie() ? { 'X-CSRFToken': csrfCookie() } : {}),
    },
    body: JSON.stringify(payload),
  })
  return parseResponse(response, '创建仿真运行失败')
}

/** 调用纯 Python planner 计算一次计划，不改变仿真执行状态。 */
export async function previewPlan(payload) {
  await ensureCsrf()
  const response = await fetch(`${API_BASE}/plans/preview/`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(csrfCookie() ? { 'X-CSRFToken': csrfCookie() } : {}),
    },
    body: JSON.stringify(payload),
  })
  return parseResponse(response, '调度计划计算失败')
}

/** 从一次 Mission 的 mask 提取真实区域并生成任务点和首轮计划。 */
export async function dispatchMission(missionId, payload = {}) {
  await ensureCsrf()
  const response = await fetch(`${API_BASE}/missions/${encodeURIComponent(missionId)}/dispatch/`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(csrfCookie() ? { 'X-CSRFToken': csrfCookie() } : {}),
    },
    body: JSON.stringify(payload),
  })
  return parseResponse(response, '任务区域生成失败')
}

/** 将手动或外部补充的区域转换为 TaskPoint。 */
export async function generateTaskPoints(payload) {
  await ensureCsrf()
  const response = await fetch(`${API_BASE}/tasks/generate/`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(csrfCookie() ? { 'X-CSRFToken': csrfCookie() } : {}),
    },
    body: JSON.stringify(payload),
  })
  return parseResponse(response, '任务点生成失败')
}

/** 更新仿真状态和汇总指标。后端使用 query string 传递仿真 ID。 */
export async function updateSimulationRun(simulationId, payload) {
  await ensureCsrf()
  const response = await fetch(`${API_BASE}/simulation-runs/?simulation_id=${encodeURIComponent(simulationId)}`, {
    method: 'PATCH',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(csrfCookie() ? { 'X-CSRFToken': csrfCookie() } : {}),
    },
    body: JSON.stringify(payload),
  })
  return parseResponse(response, '更新仿真运行失败')
}

/** 为仿真运行追加故障、重规划或新增任务事件。 */
export async function createSimulationEvent(simulationId, payload) {
  await ensureCsrf()
  const response = await fetch(`${API_BASE}/simulation-runs/${encodeURIComponent(simulationId)}/events/`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(csrfCookie() ? { 'X-CSRFToken': csrfCookie() } : {}),
    },
    body: JSON.stringify(payload),
  })
  return parseResponse(response, '记录仿真事件失败')
}

/** 触发事件并调用风险加权动态重规划。 */
export async function replanSimulation(simulationId, payload = {}) {
  await ensureCsrf()
  const response = await fetch(`${API_BASE}/simulation-runs/${encodeURIComponent(simulationId)}/replan/`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(csrfCookie() ? { 'X-CSRFToken': csrfCookie() } : {}),
    },
    body: JSON.stringify(payload),
  })
  return parseResponse(response, '动态重规划失败')
}

/** 上传一张图像并调用 FloodNet 语义分割模型。 */
export async function recognizeImage(file, modelArtifactId = '', missionId = '') {
  await ensureCsrf()
  const form = new FormData()
  form.append('image', file)
  if (modelArtifactId) form.append('model_artifact_id', modelArtifactId)
  if (missionId) form.append('mission_id', missionId)
  const response = await fetch(`${API_BASE}/vision/infer/`, {
    method: 'POST',
    body: form,
    headers: {
      Accept: 'application/json',
      ...(csrfCookie() ? { 'X-CSRFToken': csrfCookie() } : {}),
    },
  })
  return (await parseResponse(response, '模型接口请求失败')) || {}
}

