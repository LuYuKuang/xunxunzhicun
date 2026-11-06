<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

import {
  fetchCollection,
  fetchDisasterCategories,
  fetchHealth,
  fetchResource,
  createSimulationEvent,
  createSimulationRun,
  dispatchMission,
  generateTaskPoints,
  previewPlan,
  replanSimulation,
  recognizeImage,
  updateSimulationRun,
  updateMission,
  uploadImage,
} from './api/client'

const activeView = ref('overview')
const selectedAlgorithm = ref('风险加权 PSO')
const selectedTask = ref(null)
const selectedUav = ref(null)
const uploadedName = ref('')
const imagePreview = ref('')
const selectedFile = ref(null)
const recognitionResult = ref(null)
const inputImageUrl = ref('')
const maskImageUrl = ref('')
const imageWidth = ref(0)
const imageHeight = ref(0)
const showMapMask = ref(false)
const missionRegions = ref([])
const dispatchNote = ref('')
const recognitionError = ref('')
const recognitionReady = ref(false)
const isProcessing = ref(false)
const showMask = ref(true)
const fileInput = ref(null)
const isRunning = ref(false)
const simulationProgress = ref(0)
const simulationStatus = ref('等待真实任务')
const simulationTimer = ref(null)
const animationFrame = ref(null)
const previousRoutes = ref({})
const manualTaskLoading = ref(false)
const simulationRunId = ref(null)
const simulationPlan = ref(null)
const simulationError = ref('')
const failedUav = ref('')
const dataMenuOpen = ref(true)
const activeDataGroup = ref('data-assets')
const tableRows = ref([])
const tableCount = ref(0)
const tableLoading = ref(false)
const tableError = ref('')
const missionRows = ref([])
const missionCount = ref(0)
const missionLoading = ref(false)
const missionError = ref('')
const missionStatusFilter = ref('')
const selectedMissionId = ref(null)
const missionDetail = ref(null)
const missionDetailLoading = ref(false)
const missionDetailError = ref('')
const missionTaskPoints = ref([])
const missionSimulationRuns = ref([])
const taskPointRows = ref([])
const taskPointCount = ref(0)
const taskPointLoading = ref(false)
const taskPointError = ref('')
const taskPointCategoryFilter = ref('')
const taskPointStatusFilter = ref('')
const disasterCategoryOptions = ref([])
const healthStatus = ref(null)
const healthLoading = ref(false)
const uploadStage = ref('')

const navItems = [
  { id: 'overview', label: '总览', index: '01' },
  { id: 'recognition', label: '灾情识别', index: '02', badge: 'AI' },
  { id: 'simulation', label: '调度仿真', index: '03' },
]

const backendMenuGroups = [
  {
    id: 'data-assets',
    index: '05',
    label: '数据资产',
    items: [
      { id: 'datasets', label: '数据集中心', index: '05.1', endpoint: '/datasets/' },
      { id: 'model_artifacts', label: '模型制品', index: '05.2', endpoint: '/model-artifacts/' },
    ],
  },
  {
    id: 'mission-center',
    index: '06',
    label: '任务中心',
    items: [
      { id: 'missions', label: '复查任务', index: '06.1', endpoint: '/missions/' },
      { id: 'task_points', label: '任务点台账', index: '06.2', endpoint: '/task-points/' },
      { id: 'uavs', label: '无人机编队', index: '06.3', endpoint: '/uavs/' },
    ],
  },
  {
    id: 'simulation-lab',
    index: '07',
    label: '仿真与实验',
    items: [
      { id: 'simulation_runs', label: '仿真运行', index: '07.1', endpoint: '/simulation-runs/' },
      { id: 'simulation_events', label: '事件记录', index: '07.2', endpoint: '/simulation-events/' },
      { id: 'experiment_results', label: '实验结果', index: '07.3', endpoint: '/experiment-results/' },
    ],
  },
]

const dataTableConfigs = {
  datasets: {
    title: '数据集中心',
    eyebrow: 'DATA ASSETS / DATASETS',
    description: '管理训练数据的来源、许可证、版本和本地索引。',
    endpoint: '/datasets/',
    columns: [
      { key: 'name', label: '数据集名称' },
      { key: 'version', label: '版本' },
      { key: 'license_name', label: '许可证' },
      { key: 'categories', label: '类别' },
      { key: 'local_index_path', label: '索引路径' },
      { key: 'created_at', label: '创建时间', type: 'date' },
    ],
  },
  model_artifacts: {
    title: '模型制品',
    eyebrow: 'DATA ASSETS / MODEL ARTIFACTS',
    description: '查询已登记的模型、权重路径、数据版本和评估指标。',
    endpoint: '/model-artifacts/',
    columns: [
      { key: 'name', label: '模型名称' },
      { key: 'algorithm_type_label', label: '算法类型' },
      { key: 'data_version', label: '数据版本' },
      { key: 'weight_path', label: '权重路径' },
      { key: 'created_at', label: '创建时间', type: 'date' },
    ],
  },
  missions: {
    title: '复查任务',
    eyebrow: 'MISSION CENTER / MISSIONS',
    description: '查看航拍输入、识别状态以及绑定的模型制品。',
    endpoint: '/missions/',
    columns: [
      { key: 'name', label: '任务名称' },
      { key: 'status_label', label: '状态' },
      { key: 'input_image_path', label: '输入图像' },
      { key: 'model_artifact_id', label: '模型 ID' },
      { key: 'created_at', label: '创建时间', type: 'date' },
    ],
  },
  task_points: {
    title: '任务点台账',
    eyebrow: 'MISSION CENTER / TASK POINTS',
    description: '查看识别区域转化后的坐标、置信度、优先级和执行状态。',
    endpoint: '/task-points/',
    columns: [
      { key: 'id', label: '编号' },
      { key: 'mission_id', label: '任务 ID' },
      { key: 'disaster_category_label', label: '灾情类别' },
      { key: 'confidence', label: '置信度', type: 'percent' },
      { key: 'priority', label: '优先级' },
      { key: 'status_label', label: '状态' },
      { key: 'assigned_uav_id', label: '执行 UAV' },
    ],
  },
  uavs: {
    title: '无人机编队',
    eyebrow: 'MISSION CENTER / UAV FLEET',
    description: '查询虚拟无人机的位置、电量、载荷和实时状态。',
    endpoint: '/uavs/',
    columns: [
      { key: 'identifier', label: '编号' },
      { key: 'name', label: '名称' },
      { key: 'position_x', label: 'X 坐标' },
      { key: 'position_y', label: 'Y 坐标' },
      { key: 'battery_level', label: '电量', type: 'percent' },
      { key: 'status_label', label: '状态' },
    ],
  },
  simulation_runs: {
    title: '仿真运行',
    eyebrow: 'SIMULATION LAB / RUNS',
    description: '查询调度方法、随机种子、运行状态和汇总指标。',
    endpoint: '/simulation-runs/',
    columns: [
      { key: 'id', label: '编号' },
      { key: 'mission_id', label: '任务 ID' },
      { key: 'planning_method_label', label: '调度方法' },
      { key: 'random_seed', label: '随机种子' },
      { key: 'status_label', label: '状态' },
      { key: 'created_at', label: '创建时间', type: 'date' },
    ],
  },
  simulation_events: {
    title: '事件记录',
    eyebrow: 'SIMULATION LAB / EVENTS',
    description: '追踪故障、低电量、新增任务和动态重规划事件。',
    endpoint: '/simulation-events/',
    columns: [
      { key: 'id', label: '编号' },
      { key: 'simulation_run_id', label: '仿真 ID' },
      { key: 'event_type_label', label: '事件类型' },
      { key: 'uav_id', label: 'UAV ID' },
      { key: 'task_point_id', label: '任务点 ID' },
      { key: 'occurred_at', label: '发生时间', type: 'date' },
    ],
  },
  experiment_results: {
    title: '实验结果',
    eyebrow: 'SIMULATION LAB / EXPERIMENTS',
    description: '查看各调度基线的实验参数、指标和结果文件。',
    endpoint: '/experiment-results/',
    columns: [
      { key: 'id', label: '编号' },
      { key: 'simulation_run_id', label: '仿真 ID' },
      { key: 'baseline_method_label', label: '对比方法' },
      { key: 'metrics', label: '指标' },
      { key: 'result_file_path', label: '结果文件' },
      { key: 'created_at', label: '创建时间', type: 'date' },
    ],
  },
}

const viewMeta = {
  overview: { eyebrow: 'CONTROL CENTER', title: '项目总览', description: '从灾情识别到多机复查，掌握每一步运行状态。' },
  recognition: { eyebrow: 'VISION MODULE', title: '灾情识别', description: '上传航拍图像，提取灾情区域并生成复查任务。' },
  mission_detail: { eyebrow: 'MISSION CENTER / DETAIL', title: '任务详情', description: '查看任务状态、关联图像、任务点和仿真记录。' },
  simulation: { eyebrow: 'SWARM SIMULATION', title: '调度仿真', description: '在二维地图中观察任务分配、航线执行与动态重规划。' },
}

const tasks = ref([])

const defaultUavs = [
  { id: 'UAV-01', name: '侦察一号', color: '#78d5c5', battery: 82, status: '待命', assigned: 0, x: 0, y: 0, route: [] },
  { id: 'UAV-02', name: '侦察二号', color: '#e4bc70', battery: 64, status: '待命', assigned: 0, x: 0, y: 0, route: [] },
  { id: 'UAV-03', name: '侦察三号', color: '#9b9cf8', battery: 91, status: '待命', assigned: 0, x: 0, y: 0, route: [] },
]
const uavs = ref(cloneUavs(defaultUavs))

const recognitionClasses = ref([])

const eventLog = ref([
  { time: '刚刚', title: '等待真实识别结果', detail: '上传航拍图后提取受淹区域', tone: 'teal' },
])

const isDataView = computed(() => Boolean(dataTableConfigs[activeView.value]))
const currentMeta = computed(() => viewMeta[activeView.value] || dataTableConfigs[activeView.value] || viewMeta.overview)
const currentTable = computed(() => dataTableConfigs[activeView.value])
const completedCount = computed(() => tasks.value.filter((task) => task.status === '已完成').length)
const progressLabel = computed(() => `${Math.round(simulationProgress.value)}%`)
const activeTask = computed(() => selectedTask.value)
const plannerMetrics = computed(() => simulationPlan.value?.metrics || {})
const plannerCompletionLabel = computed(() => simulationPlan.value ? `${Math.round(Number(plannerMetrics.value.focus_task_completion_rate || plannerMetrics.value.completion_rate || 0) * 100)}%` : '—')
const plannerDistanceLabel = computed(() => simulationPlan.value ? `${Number(plannerMetrics.value.total_distance || 0).toFixed(1)} m` : '—')
const plannerTimeLabel = computed(() => simulationPlan.value ? `${Number(plannerMetrics.value.total_time || 0).toFixed(1)} s` : '—')
const mapReady = computed(() => imageWidth.value > 0 && imageHeight.value > 0 && Boolean(inputImageUrl.value))
const mapImageUrl = computed(() => (showMapMask.value && maskImageUrl.value) ? maskImageUrl.value : inputImageUrl.value)
const mapAspectRatio = computed(() => mapReady.value ? `${imageWidth.value} / ${imageHeight.value}` : '16 / 9')
const mapStrokeWidth = computed(() => Math.max(2, imageWidth.value / 320 || 2))
const mapTaskRadius = computed(() => Math.max(6, imageWidth.value / 140 || 6))
const mapLabelSize = computed(() => Math.max(10, imageWidth.value / 260 || 10))
const stats = computed(() => [
  { label: '识别置信度', value: recognitionReady.value ? `${((recognitionResult.value?.mean_confidence || 0) * 100).toFixed(1)}%` : '—', delta: recognitionReady.value ? `${recognitionResult.value?.device || 'CPU'} 推理` : '等待输入', icon: '◎', tone: 'teal' },
  { label: '复查任务点', value: `${tasks.value.length}`, delta: `${completedCount.value} 已完成`, icon: '⌖', tone: 'orange' },
  { label: '重点任务完成率', value: plannerCompletionLabel.value, delta: simulationPlan.value ? `${simulationPlan.value.algorithm} 实时计划` : '等待调度', icon: '↗', tone: 'purple' },
  { label: '预计总航程', value: plannerDistanceLabel.value, delta: simulationPlan.value ? '来自当前计划' : '等待调度', icon: '⌁', tone: 'lime' },
])

const missionProgressPercent = computed(() => {
  const total = missionTaskPoints.value.length
  if (!total) return missionRows.value[0]?.status === 'completed' ? 100 : 0
  const done = missionTaskPoints.value.filter((point) => point.status === 'completed').length
  return Math.round((done / total) * 100)
})

function cloneUavs(source) {
  return source.map((uav) => ({ ...uav, route: uav.route.map((point) => [...point]) }))
}

function uavsForImage(width, height) {
  const homeX = width * 0.5
  const homeY = height * 0.92
  return defaultUavs.map((uav, index) => {
    const x = homeX + (index - 1) * width * 0.08
    return { ...uav, x, y: homeY, route: [[x, homeY]] }
  })
}

function routePath(route) {
  return route.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point[0]} ${point[1]}`).join(' ')
}

function openView(view) {
  activeView.value = view
  if (dataTableConfigs[view] && !['missions', 'task_points'].includes(view)) loadDataView(view)
  if (view === 'missions') loadMissionList()
  if (view === 'task_points') loadTaskPointList()
}

function openDataGroup(group) {
  activeDataGroup.value = group.id
  dataMenuOpen.value = true
}

async function loadDataView(view = activeView.value) {
  const config = dataTableConfigs[view]
  if (!config) return
  tableLoading.value = true
  tableError.value = ''
  try {
    const result = await fetchCollection(config.endpoint)
    tableRows.value = result.items || []
    tableCount.value = result.count || 0
  } catch (error) {
    tableRows.value = []
    tableCount.value = 0
    tableError.value = error.message || '暂时无法读取数据库数据。'
  } finally {
    tableLoading.value = false
  }
}

async function loadMissionList() {
  missionLoading.value = true
  missionError.value = ''
  try {
    const params = missionStatusFilter.value ? { status: missionStatusFilter.value } : {}
    const result = await fetchCollection('/missions/', params)
    missionRows.value = result.items || []
    missionCount.value = result.count || 0
  } catch (error) {
    missionRows.value = []
    missionCount.value = 0
    missionError.value = error.message || '暂时无法读取任务数据。'
  } finally {
    missionLoading.value = false
  }
}

async function loadTaskPointList() {
  taskPointLoading.value = true
  taskPointError.value = ''
  try {
    const params = {}
    if (taskPointCategoryFilter.value) params.disaster_category = taskPointCategoryFilter.value
    if (taskPointStatusFilter.value) params.status = taskPointStatusFilter.value
    const result = await fetchCollection('/task-points/', params)
    taskPointRows.value = result.items || []
    taskPointCount.value = result.count || 0
  } catch (error) {
    taskPointRows.value = []
    taskPointCount.value = 0
    taskPointError.value = error.message || '暂时无法读取任务点数据。'
  } finally {
    taskPointLoading.value = false
  }
}

async function loadMissionDetail(missionId, navigate = true) {
  if (!missionId) return
  selectedMissionId.value = missionId
  if (navigate) activeView.value = 'mission_detail'
  missionDetailLoading.value = true
  missionDetailError.value = ''
  try {
    const [mission, taskPoints, runs] = await Promise.all([
      fetchResource(`/missions/${missionId}/`),
      fetchCollection('/task-points/', { mission_id: missionId }),
      fetchCollection('/simulation-runs/', { mission_id: missionId }),
    ])
    missionDetail.value = mission
    missionTaskPoints.value = taskPoints.items || []
    missionSimulationRuns.value = runs.items || []
  } catch (error) {
    missionDetail.value = null
    missionTaskPoints.value = []
    missionSimulationRuns.value = []
    missionDetailError.value = error.message || '任务详情读取失败。'
  } finally {
    missionDetailLoading.value = false
  }
}

function openMissionDetail(missionId) {
  loadMissionDetail(missionId)
}

function backToMissionList() {
  openView('missions')
}

async function changeMissionStatus(status) {
  if (!missionDetail.value) return
  missionDetailError.value = ''
  try {
    missionDetail.value = await updateMission(missionDetail.value.id, { status })
    await loadMissionList()
  } catch (error) {
    missionDetailError.value = error.message || '任务状态更新失败。'
  }
}

async function loadHealth() {
  healthLoading.value = true
  try {
    healthStatus.value = await fetchHealth()
  } catch (error) {
    healthStatus.value = { status: 'error', error: error.message || '服务不可用' }
  } finally {
    healthLoading.value = false
  }
}

async function loadDisasterCategories() {
  try {
    const result = await fetchDisasterCategories()
    disasterCategoryOptions.value = result.items || []
  } catch {
    disasterCategoryOptions.value = []
  }
}

function formatCell(value, column) {
  if (value === null || value === undefined || value === '') return '—'
  if (column.type === 'percent') return `${(Number(value) * (Number(value) <= 1 ? 100 : 1)).toFixed(1)}%`
  if (column.type === 'date') return String(value).replace('T', ' ').slice(0, 19)
  if (Array.isArray(value)) return value.join('、') || '—'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function openFilePicker() {
  fileInput.value?.click()
}

function setFile(file) {
  if (!file) return
  if (!file.type.startsWith('image/')) {
    recognitionError.value = '请选择 JPG、PNG 或 WEBP 图片。'
    return
  }
  if (file.size > 20 * 1024 * 1024) {
    recognitionError.value = '图片不能超过 20 MB。'
    return
  }
  selectedFile.value = file
  uploadedName.value = file.name
  recognitionReady.value = false
  recognitionResult.value = null
  inputImageUrl.value = ''
  maskImageUrl.value = ''
  imageWidth.value = 0
  imageHeight.value = 0
  missionRegions.value = []
  dispatchNote.value = ''
  tasks.value = []
  simulationPlan.value = null
  recognitionError.value = ''
  if (imagePreview.value) URL.revokeObjectURL(imagePreview.value)
  imagePreview.value = URL.createObjectURL(file)
}

function handleFile(event) {
  setFile(event.target.files?.[0])
  event.target.value = ''
}

function handleDrop(event) {
  setFile(event.dataTransfer.files?.[0])
}

function loadSample() {
  activeView.value = 'recognition'
  recognitionError.value = '请先选择一张航拍图像；模型推理需要真实的 image 文件。'
}

async function runRecognition() {
  if (isProcessing.value) return
  if (!selectedFile.value) {
    loadSample()
    return
  }
  isProcessing.value = true
  uploadStage.value = '正在上传图片…'
  recognitionError.value = ''
  try {
    const uploaded = await uploadImage(selectedFile.value)
    uploadStage.value = '图片已保存，正在请求模型识别…'
    const result = await recognizeImage(selectedFile.value, '', uploaded.mission_id)
    recognitionResult.value = result
    imageWidth.value = Number(result.width || 0)
    imageHeight.value = Number(result.height || 0)
    inputImageUrl.value = result.input_image_url || imagePreview.value
    maskImageUrl.value = result.mask_url || ''
    showMapMask.value = false
    uavs.value = uavsForImage(imageWidth.value, imageHeight.value)
    const colors = ['#6c768d', '#ef8d73', '#9aa0a8', '#e4bc70', '#9aa0a8', '#78d5c5', '#70a674', '#9b9cf8', '#5ba6de', '#9ab267']
    recognitionClasses.value = (result.class_stats || []).map((item) => ({
      label: item.label,
      value: Math.max(0, Math.min(100, Number(item.ratio || 0) * 100)),
      confidence: `${(Number(item.confidence || 0) * 100).toFixed(1)}%`,
      color: colors[item.id] || '#6c768d',
    })).filter((item) => item.value > 0)
    recognitionReady.value = true
    uploadStage.value = '识别完成，正在提取真实受淹区域…'
    const dispatched = await dispatchMission(result.mission_id, {
      min_area_px: 2000,
      max_regions: 12,
      coordinate_scale: 0.1,
      algorithm: planningMethodValues[selectedAlgorithm.value] || 'risk_aware_pso',
      map_state: {
        width: imageWidth.value,
        height: imageHeight.value,
        home: { x: imageWidth.value * 0.5, y: imageHeight.value * 0.92 },
      },
    })
    missionRegions.value = dispatched.regions || []
    dispatchNote.value = dispatched.note || ''
    tasks.value = (dispatched.tasks || []).map((item) => {
      const region = missionRegions.value.find((candidate) =>
        Math.round(candidate.x) === Math.round(item.coordinate_x)
        && Math.round(candidate.y) === Math.round(item.coordinate_y))
      const priority = Number(item.priority || 0)
      return {
        id: String(item.id),
        label: region?.id || `区域 ${item.id}`,
        type: item.disaster_category_label || item.disaster_category,
        level: priority >= 100 ? '高' : priority >= 50 ? '中' : '低',
        score: Number(item.confidence || 0),
        status: item.status_label || '待复查',
        x: Number(item.coordinate_x || 0),
        y: Number(item.coordinate_y || 0),
        areaPx: Number(item.area || 0),
        areaRatio: Number(region?.area_ratio || 0),
        category: item.disaster_category,
        priority,
        source: 'model',
      }
    })
    simulationPlan.value = dispatched.plan || null
    await loadMissionList()
    await loadMissionDetail(result.mission_id, false)
    eventLog.value.unshift({
      time: '刚刚',
      title: '模型识别完成',
      detail: `${result.width} × ${result.height} · ${tasks.value.length} 个真实区域`,
      tone: 'success',
    })
    if (!tasks.value.length) {
      eventLog.value.unshift({ time: '刚刚', title: '未检出受淹区域', detail: '可在图片上手动补充复查点', tone: 'orange' })
    }
  } catch (error) {
    recognitionError.value = error.message || '模型识别失败。'
    recognitionReady.value = false
  } finally {
    isProcessing.value = false
    uploadStage.value = ''
  }
}

function toggleTask(task) {
  selectedTask.value = selectedTask.value?.id === task.id ? null : task
}

function selectUav(uav) {
  selectedUav.value = selectedUav.value?.id === uav.id ? null : uav
}

async function handleMapClick(event) {
  if (!mapReady.value || tasks.value.length || manualTaskLoading.value) return
  const missionId = missionDetail.value?.id || selectedMissionId.value
  if (!missionId) return
  const bounds = event.currentTarget.getBoundingClientRect()
  const x = Math.max(0, Math.min(imageWidth.value, ((event.clientX - bounds.left) / bounds.width) * imageWidth.value))
  const y = Math.max(0, Math.min(imageHeight.value, ((event.clientY - bounds.top) / bounds.height) * imageHeight.value))
  manualTaskLoading.value = true
  try {
    const result = await generateTaskPoints({
      mission_id: missionId,
      regions: [{
        id: `manual-${Date.now()}`,
        x: Math.round(x),
        y: Math.round(y),
        category: 'flooded_area',
        area: 0,
        confidence: 0,
        manual: true,
      }],
      replace_pending: false,
    })
    const item = result.items?.[0]
    if (!item) return
    const task = {
      id: String(item.id),
      label: '手动',
      type: item.disaster_category_label || item.disaster_category,
      level: '高',
      score: Number(item.confidence || 0),
      status: item.status_label || '待复查',
      x: Number(item.coordinate_x || x),
      y: Number(item.coordinate_y || y),
      areaPx: Number(item.area || 0),
      areaRatio: 0,
      category: item.disaster_category,
      priority: Number(item.priority || 0),
      source: 'manual',
    }
    tasks.value.push(task)
    dispatchNote.value = ''
    eventLog.value.unshift({ time: '刚刚', title: '已补充手动复查点', detail: `(${task.x}, ${task.y}) · 将参与下一次规划`, tone: 'orange' })
  } catch (error) {
    simulationError.value = error.message || '手动任务点生成失败。'
  } finally {
    manualTaskLoading.value = false
  }
}

const planningMethodValues = {
  平均分配: 'round_robin',
  最近邻: 'nearest',
  '标准 PSO': 'pso',
  '风险加权 PSO': 'risk_aware_pso',
}

function simulationTaskSnapshot() {
  return tasks.value.map((task) => ({
    id: task.id,
    label: task.label,
    disaster_category: task.category || task.type,
    priority: Number(task.priority || 0),
    confidence: task.score,
    coordinate_x: task.x,
    coordinate_y: task.y,
    status: task.status === '已完成' ? 'completed' : 'pending',
  }))
}

function simulationUavSnapshot() {
  return uavs.value.map((uav) => ({
    identifier: uav.id,
    name: uav.name,
    battery_level: uav.battery,
    status: uav.status,
    position_x: uav.x,
    position_y: uav.y,
    assigned: uav.assigned,
    route: uav.route,
  }))
}

function routeLength(route) {
  return (route || []).slice(1).reduce((total, point, index) => {
    const previous = route[index]
    return total + Math.hypot(Number(point[0]) - Number(previous[0]), Number(point[1]) - Number(previous[1]))
  }, 0)
}

function pointAtDistance(route, distance) {
  if (!route?.length) return [0, 0]
  if (route.length === 1 || distance <= 0) return [...route[0]]
  let travelled = 0
  for (let index = 1; index < route.length; index += 1) {
    const previous = route[index - 1]
    const current = route[index]
    const segment = Math.hypot(current[0] - previous[0], current[1] - previous[1])
    if (travelled + segment >= distance) {
      const ratio = segment ? (distance - travelled) / segment : 0
      return [
        previous[0] + (current[0] - previous[0]) * ratio,
        previous[1] + (current[1] - previous[1]) * ratio,
      ]
    }
    travelled += segment
  }
  return [...route[route.length - 1]]
}

function distanceToRoutePoint(route, pointIndex) {
  return (route || []).slice(1, pointIndex + 1).reduce((total, point, index) => {
    const previous = route[index]
    return total + Math.hypot(Number(point[0]) - Number(previous[0]), Number(point[1]) - Number(previous[1]))
  }, 0)
}

function applyPlanToScene(plan, { keepPrevious = false } = {}) {
  if (!plan?.routes) return
  if (keepPrevious) {
    previousRoutes.value = Object.fromEntries(uavs.value
      .filter((uav) => uav.route?.length > 1)
      .map((uav) => [uav.id, uav.route.map((point) => [...point])]))
  } else {
    previousRoutes.value = {}
  }
  const assignments = plan.assignments || {}
  tasks.value.forEach((task) => {
    const assigned = Object.values(assignments).some((items) => items.includes(task.id))
    if (assigned && task.status !== '已完成') task.status = '执行中'
  })
  uavs.value.forEach((uav) => {
    const route = plan.routes[uav.id]
    if (!route) return
    const points = [route.start, ...(route.tasks || []), route.return].filter(Boolean)
    uav.route = points.map((point) => [Number(point.x), Number(point.y)])
    uav.routeTaskIds = (route.tasks || []).map((point) => String(point.task_id))
    if (uav.route.length) {
      uav.x = uav.route[0][0]
      uav.y = uav.route[0][1]
    }
    uav.assigned = (route.tasks || []).length
    if (uav.status !== '故障退出') uav.status = uav.assigned ? '执行中' : '待命'
  })
}

function startRouteAnimation() {
  if (animationFrame.value) cancelAnimationFrame(animationFrame.value)
  const startedAt = performance.now()
  const duration = Math.max(2500, Math.min(12000, (simulationPlan.value?.metrics?.total_time || 8) * 1000))
  const frame = (now) => {
    const progress = Math.min(1, (now - startedAt) / duration)
    simulationProgress.value = progress * 100
    uavs.value.forEach((uav) => {
      const routeDistance = routeLength(uav.route)
      const point = pointAtDistance(uav.route, routeDistance * progress)
      uav.x = point[0]
      uav.y = point[1]
      ;(uav.routeTaskIds || []).forEach((taskId, index) => {
        const task = tasks.value.find((item) => String(item.id) === String(taskId))
        if (!task || task.status === '已完成') return
        if (progress * routeDistance >= distanceToRoutePoint(uav.route, index + 1)) task.status = '已完成'
      })
    })
    if (progress < 1) {
      animationFrame.value = requestAnimationFrame(frame)
    } else {
      animationFrame.value = null
      finishSimulation()
    }
  }
  animationFrame.value = requestAnimationFrame(frame)
}

async function finishSimulation() {
  const runId = simulationRunId.value
  isRunning.value = false
  simulationProgress.value = 100
  simulationStatus.value = '仿真已完成'
  if (animationFrame.value) cancelAnimationFrame(animationFrame.value)
  animationFrame.value = null
  tasks.value.forEach((task) => { task.status = '已完成' })
  uavs.value.forEach((uav) => { if (uav.status !== '故障退出') uav.status = '已完成' })
  eventLog.value.unshift({ time: '刚刚', title: '仿真运行完成', detail: `${selectedAlgorithm.value} · ${tasks.value.length} 个任务点`, tone: 'success' })
  if (!runId) return
  try {
    const run = await updateSimulationRun(runId, {
      status: 'completed',
      summary_metrics: {
        completion_rate: tasks.value.length ? completedCount.value / tasks.value.length : 0,
        planned_distance_km: Number(((simulationPlan.value?.metrics?.total_distance || 0) / 100).toFixed(3)),
        task_count: tasks.value.length,
        uav_count: uavs.value.length,
        map_state: {
          width: imageWidth.value,
          height: imageHeight.value,
          home: { x: imageWidth.value * 0.5, y: imageHeight.value * 0.92 },
        },
        coordinate_scale: 0.1,
        routes: simulationPlan.value?.routes || {},
        ...(simulationPlan.value?.metrics || {}),
        planner: simulationPlan.value || {},
      },
    })
    if (missionDetail.value?.id === run.mission_id) {
      missionSimulationRuns.value = [run, ...missionSimulationRuns.value.filter((item) => item.id !== run.id)]
    }
  } catch (error) {
    simulationError.value = error.message || '仿真已完成，但结果回写失败。'
  }
}

async function startSimulation() {
  if (isRunning.value) return
  const missionId = missionDetail.value?.id || selectedMissionId.value
  if (!missionId || !mapReady.value) {
    simulationError.value = '请先完成一次图像识别，再进入调度仿真。'
    simulationStatus.value = '缺少可调度任务'
    return
  }
  if (!tasks.value.length) {
    simulationError.value = dispatchNote.value || '未检出受淹区域，请在底图上手动补充任务点。'
    simulationStatus.value = '没有可调度任务'
    return
  }
  simulationError.value = ''
  isRunning.value = true
  simulationStatus.value = '仿真运行中'
  simulationProgress.value = 0
  if (animationFrame.value) cancelAnimationFrame(animationFrame.value)
  try {
    const planningMethod = planningMethodValues[selectedAlgorithm.value] || 'risk_aware_pso'
    const plan = await previewPlan({
      mission_id: missionId,
      algorithm: planningMethod,
      random_seed: 42,
      tasks: simulationTaskSnapshot(),
      uav_configuration: simulationUavSnapshot(),
      coordinate_scale: 0.1,
      map_state: {
        width: imageWidth.value,
        height: imageHeight.value,
        home: { x: imageWidth.value * 0.5, y: imageHeight.value * 0.92 },
      },
      config: { population_size: 16, iterations: 24, energy_per_distance: 0.08 },
    })
    simulationPlan.value = plan
    applyPlanToScene(plan, { keepPrevious: false })
    const run = await createSimulationRun({
      mission_id: missionId,
      planning_method: planningMethod,
      random_seed: 42,
      status: 'running',
      uav_configuration: simulationUavSnapshot(),
      task_snapshot: simulationTaskSnapshot(),
      summary_metrics: {
        ...(plan.metrics || {}),
        objective_value: plan.objective_value,
        planner: plan,
        map_state: {
          width: imageWidth.value,
          height: imageHeight.value,
          home: { x: imageWidth.value * 0.5, y: imageHeight.value * 0.92 },
        },
        coordinate_scale: 0.1,
        routes: plan.routes || {},
      },
    })
    simulationRunId.value = run.id
    simulationStatus.value = `仿真运行中 · #${run.id}`
    eventLog.value.unshift({ time: '刚刚', title: '仿真运行已创建', detail: `${selectedAlgorithm.value} · Mission #${missionId}`, tone: 'teal' })
    startRouteAnimation()
  } catch (error) {
    isRunning.value = false
    simulationRunId.value = null
    simulationStatus.value = '仿真启动失败'
    simulationError.value = error.message || '无法创建仿真运行记录。'
  }
}

async function triggerEvent(type) {
  simulationError.value = ''
  const runId = simulationRunId.value
  if (type === '故障') {
    failedUav.value = 'UAV-02'
    const target = uavs.value.find((uav) => uav.id === 'UAV-02')
    if (target) {
      target.status = '故障退出'
      target.battery = 14
    }
    simulationStatus.value = '已触发动态重规划'
    simulationProgress.value = Math.max(simulationProgress.value, 48)
    eventLog.value.unshift({ time: '刚刚', title: 'UAV-02 故障退出', detail: '剩余任务已重新分配给 UAV-01 / UAV-03', tone: 'danger' })
    if (runId) {
      try {
        if (animationFrame.value) cancelAnimationFrame(animationFrame.value)
        const plan = await replanSimulation(runId, {
          event_type: 'uav_failure',
          uav_id: 'UAV-02',
          config: { algorithm: 'risk_aware_pso', random_seed: 42, population_size: 16, iterations: 20 },
        })
        simulationPlan.value = plan
        applyPlanToScene(plan, { keepPrevious: true })
        startRouteAnimation()
      } catch (error) {
        simulationError.value = error.message || '故障事件回写失败。'
      }
    }
  } else {
    const newTask = {
      id: `T-${String(tasks.value.length + 1).padStart(3, '0')}`,
      label: '新增临时复查点',
      type: '受淹区域',
      level: '高',
      score: 0.82,
      status: '待复查',
      x: imageWidth.value * 0.58,
      y: imageHeight.value * 0.42,
      category: 'flooded_area',
      priority: 12,
      areaPx: 0,
      areaRatio: 0,
      source: 'event',
    }
    tasks.value.push(newTask)
    simulationStatus.value = '新增任务等待分配'
    eventLog.value.unshift({ time: '刚刚', title: '新增 1 个复查任务', detail: '调度器正在计算最短增量航线', tone: 'orange' })
    if (runId) {
      try {
        if (animationFrame.value) cancelAnimationFrame(animationFrame.value)
        const plan = await replanSimulation(runId, {
          event_type: 'task_added',
          task: { id: newTask.id, x: newTask.x, y: newTask.y, category: 'flooded_area', area: 0, confidence: newTask.score, priority: 12, status: 'pending' },
          config: { algorithm: 'risk_aware_pso', random_seed: 42, population_size: 16, iterations: 20 },
        })
        simulationPlan.value = plan
        applyPlanToScene(plan, { keepPrevious: true })
        startRouteAnimation()
      } catch (error) {
        simulationError.value = error.message || '新增任务事件回写失败。'
      }
    }
  }
}

function resetSimulation() {
  if (simulationRunId.value && isRunning.value) {
    updateSimulationRun(simulationRunId.value, { status: 'cancelled' }).catch(() => {})
  }
  if (animationFrame.value) cancelAnimationFrame(animationFrame.value)
  animationFrame.value = null
  isRunning.value = false
  simulationRunId.value = null
  simulationPlan.value = null
  simulationError.value = ''
  failedUav.value = ''
  simulationProgress.value = 0
  simulationStatus.value = tasks.value.length ? '等待开始仿真' : '等待真实任务'
  previousRoutes.value = {}
  uavs.value = mapReady.value ? uavsForImage(imageWidth.value, imageHeight.value) : cloneUavs(defaultUavs)
  eventLog.value = [{ time: '刚刚', title: '等待真实任务', detail: tasks.value.length ? `${tasks.value.length} 个区域 · ${uavs.value.length} 架虚拟无人机` : '上传并识别航拍图像后开始', tone: 'teal' }]
}

onUnmounted(() => {
  clearInterval(simulationTimer.value)
  if (animationFrame.value) cancelAnimationFrame(animationFrame.value)
  if (imagePreview.value) URL.revokeObjectURL(imagePreview.value)
})

onMounted(() => {
  loadMissionList()
  loadTaskPointList()
  loadDisasterCategories()
  loadHealth()
})
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand-lockup">
        <div class="brand-mark"><span></span><span></span><span></span></div>
        <div>
          <strong>汛巡智群</strong>
          <small>SWARM INTELLIGENCE</small>
        </div>
      </div>

      <div class="sidebar-section-label">工作台 / WORKSPACE</div>
      <nav class="main-nav" aria-label="主导航">
        <button v-for="item in navItems" :key="item.id" class="nav-item" :class="{ active: activeView === item.id }" :aria-current="activeView === item.id ? 'page' : undefined" @click="openView(item.id)">
          <span class="nav-index">{{ item.index }}</span>
          <span class="nav-label">{{ item.label }}</span>
          <span v-if="item.badge" class="nav-badge">{{ item.badge }}</span>
          <span v-else class="nav-arrow">↗</span>
        </button>
      </nav>

      <div class="backend-nav">
        <button class="backend-nav-title" :class="{ active: isDataView }" :aria-expanded="dataMenuOpen" @click="dataMenuOpen = !dataMenuOpen">
          <span class="nav-index">DB</span><span>数据后台</span><span class="backend-chevron">{{ dataMenuOpen ? '⌃' : '⌄' }}</span>
        </button>
        <div v-show="dataMenuOpen" class="backend-groups">
          <div v-for="group in backendMenuGroups" :key="group.id" class="backend-group">
            <button class="backend-group-title" :class="{ expanded: activeDataGroup === group.id }" @click="openDataGroup(group)"><span>{{ group.index }}</span><strong>{{ group.label }}</strong><i>{{ activeDataGroup === group.id ? '−' : '+' }}</i></button>
            <div v-show="activeDataGroup === group.id" class="backend-subnav">
              <button v-for="item in group.items" :key="item.id" class="backend-subnav-item" :class="{ active: activeView === item.id }" @click="openView(item.id)"><span>{{ item.index }}</span>{{ item.label }}<b v-if="activeView === item.id">●</b></button>
            </div>
          </div>
        </div>
      </div>

      <div class="sidebar-divider"></div>
      <div class="sidebar-section-label">运行状态 / STATUS</div>
      <div class="system-status">
        <span class="status-dot" :class="{ 'status-dot-error': healthStatus?.status === 'error' }"></span>
        <div><strong>{{ healthLoading ? '正在检查服务' : healthStatus?.status === 'error' ? '接口连接异常' : '系统运行正常' }}</strong><small>{{ healthStatus?.model?.status === 'ready' ? '模型依赖和权重已就绪' : '模型服务按需加载' }}</small></div>
      </div>
      <div class="model-status">
        <div class="status-line"><span>模型</span><strong>FloodNet · 10 类分割</strong></div>
        <div class="status-line"><span>设备</span><strong class="device-ready">CPU / GPU · 按需</strong></div>
      </div>

      <div class="sidebar-footer">
        <div class="profile-avatar">侯</div>
        <div class="profile-copy"><strong>侯忆雪</strong><small>项目负责人</small></div>
        <span class="profile-more">•••</span>
      </div>
    </aside>

    <main class="main-content">
      <header class="top-header">
        <div class="breadcrumbs"><span>汛巡智群</span><b>/</b><strong>{{ currentMeta.title }}</strong></div>
        <div class="header-actions">
          <div class="live-pill" :class="{ 'connection-error': healthStatus?.status === 'error' }"><span></span>{{ healthLoading || !healthStatus ? '检查连接中' : healthStatus.status === 'error' ? '服务未连接' : '服务已连接' }}</div>
          <a class="admin-link" href="/admin/">管理后台 <span>↗</span></a>
        </div>
      </header>

      <div class="content-wrap">
        <section class="page-intro">
          <div>
            <p class="section-kicker">{{ currentMeta.eyebrow }}</p>
            <h1>{{ currentMeta.title }}</h1>
            <p>{{ currentMeta.description }}</p>
          </div>
        </section>

        <section v-if="activeView === 'overview'" class="view-stack">
          <div class="hero-card">
            <div class="hero-card-copy">
              <span class="hero-tag">FIELD INTELLIGENCE / 01</span>
              <h2>让灾情复查<br /><em>更快更精准</em></h2>
              <p>从航拍图像中识别灾情，将不确定性转化为任务优先级，让多架无人机在有限电量下协同完成复查。</p>
              <button class="solid-button" @click="openView('recognition')">开始一次识别 <span>→</span></button>
            </div>
            <div class="hero-visual" aria-hidden="true">
              <div class="scene-frame"><span></span><span></span><span></span><span></span></div>
              <div class="scene-caption"><span>FIELD VIEW / 场景示意</span><strong>从感知到行动</strong><small>航拍识别 · 任务提取 · 协同调度</small></div>
            </div>
          </div>

          <div class="stats-grid">
            <article v-for="stat in stats" :key="stat.label" class="stat-card" :class="`tone-${stat.tone}`">
              <div class="stat-top"><span>{{ stat.label }}</span><b>{{ stat.icon }}</b></div>
              <strong>{{ stat.value }}</strong>
              <small>{{ stat.delta }}</small>
            </article>
          </div>

          <div class="two-column-grid">
            <article class="panel recent-panel">
              <div class="panel-heading"><div><span class="panel-kicker">LATEST MISSION</span><h2>最近一次任务</h2></div><button class="text-button" @click="openView('simulation')">查看仿真 <span>→</span></button></div>
              <div v-if="missionLoading" class="table-state home-inline-state"><span class="loading-ring"></span><strong>正在读取最近任务…</strong></div>
              <div v-else-if="missionError" class="table-state table-error home-inline-state"><span>!</span><strong>{{ missionError }}</strong><button class="text-button" @click="loadMissionList">重试 <span>↻</span></button></div>
              <button v-else-if="missionRows.length" class="mission-summary mission-summary-button" @click="openMissionDetail(missionRows[0].id)">
                
                <div class="mission-info"><div class="mission-title"><strong>{{ missionRows[0].name }}</strong><span class="success-tag">{{ missionRows[0].status_label || missionRows[0].status }}</span></div><p>{{ missionRows[0].input_image_path || '尚未关联航拍图像' }}</p><div class="progress-track"><span :style="{ width: `${missionProgressPercent}%` }"></span></div><div class="mission-foot"><span>{{ missionTaskPoints.length || '—' }} 个任务点</span><span>Mission #{{ missionRows[0].id }}</span><span>点击查看详情</span></div></div>
              </button>
              <div v-else class="table-state home-inline-state"><span>∅</span><strong>暂无任务记录</strong><button class="text-button" @click="openView('recognition')">上传图片创建任务 <span>→</span></button></div>
            </article>

            <article class="panel event-panel">
              <div class="panel-heading"><div><span class="panel-kicker">ACTIVITY LOG</span><h2>运行动态</h2></div><span class="live-small"><i></i>实时</span></div>
              <div class="event-list"><div v-for="event in eventLog.slice(0, 3)" :key="`${event.time}-${event.title}`" class="event-item"><span class="event-marker" :class="`event-${event.tone}`"></span><div><strong>{{ event.title }}</strong><p>{{ event.detail }}</p></div><time>{{ event.time }}</time></div></div>
            </article>
          </div>

          <section class="workflow-panel">
            <div class="workflow-heading"><div><span class="panel-kicker">WORKFLOW</span><h2>从图像到行动</h2></div><span>04 STEPS</span></div>
            <div class="workflow-steps"><div class="workflow-step done"><span>01</span><div><strong>航拍识别</strong><small>提取灾情区域</small></div></div><i>→</i><div class="workflow-step done"><span>02</span><div><strong>任务生成</strong><small>计算复查优先级</small></div></div><i>→</i><div class="workflow-step active"><span>03</span><div><strong>协同调度</strong><small>规划多机航线</small></div></div><i>→</i><div class="workflow-step"><span>04</span><div><strong>动态复查</strong><small>响应突发事件</small></div></div></div>
          </section>
        </section>

        <section v-else-if="activeView === 'missions'" class="view-stack">
          <div class="data-view-toolbar">
            <div class="data-view-context"><span class="database-pulse"></span><span>MISSION CENTER</span><b>任务列表来自 Django API</b></div>
            <button class="outline-button" :disabled="missionLoading" @click="loadMissionList">{{ missionLoading ? '读取中…' : '刷新任务' }} <span>↻</span></button>
          </div>
          <article class="panel mission-list-panel">
            <div class="panel-heading"><div><span class="panel-kicker">MISSION CENTER / LIST</span><h2>复查任务</h2></div><span class="table-note">{{ missionCount }} RECORDS</span></div>
            <div class="resource-filter-row">
              <label>任务状态<select v-model="missionStatusFilter" @change="loadMissionList"><option value="">全部状态</option><option value="created">已创建</option><option value="inferencing">识别中</option><option value="ready">待调度</option><option value="planning">规划中</option><option value="running">执行中</option><option value="completed">已完成</option><option value="failed">失败</option></select></label>
              <button class="text-button" @click="openView('recognition')">上传图片创建任务 <span>→</span></button>
            </div>
            <div v-if="missionLoading" class="table-state"><span class="loading-ring"></span><strong>正在读取任务列表…</strong></div>
            <div v-else-if="missionError" class="table-state table-error"><span>!</span><strong>{{ missionError }}</strong><button class="text-button" @click="loadMissionList">重试 <span>↻</span></button></div>
            <div v-else-if="!missionRows.length" class="table-state"><span>∅</span><strong>暂无复查任务</strong><small>上传一张航拍图片即可创建第一条任务。</small><button class="solid-button compact" @click="openView('recognition')">开始上传 <span>→</span></button></div>
            <div v-else class="mission-card-list">
              <button v-for="mission in missionRows" :key="mission.id" class="mission-card-row" @click="openMissionDetail(mission.id)">
                <span class="mission-card-index">#{{ mission.id }}</span>
                <span class="mission-card-main"><strong>{{ mission.name }}</strong><small>{{ mission.input_image_path || '尚未关联图片' }}</small></span>
                <span class="status-chip" :class="`status-${mission.status}`">{{ mission.status_label || mission.status }}</span>
                <span class="mission-card-date">{{ formatCell(mission.created_at, { type: 'date' }) }}</span>
                <span class="mission-card-arrow">→</span>
              </button>
            </div>
          </article>
        </section>

        <section v-else-if="activeView === 'mission_detail'" class="view-stack">
          <div class="detail-toolbar"><button class="outline-button" @click="backToMissionList">← 返回任务列表</button><span class="detail-context">MISSION CENTER / DETAIL</span></div>
          <div v-if="missionDetailLoading" class="panel table-state detail-state"><span class="loading-ring"></span><strong>正在读取任务详情…</strong></div>
          <div v-else-if="missionDetailError" class="panel table-state table-error detail-state"><span>!</span><strong>{{ missionDetailError }}</strong><button class="text-button" @click="loadMissionDetail(selectedMissionId)">重试 <span>↻</span></button></div>
          <div v-else-if="!missionDetail" class="panel table-state detail-state"><span>∅</span><strong>未找到任务</strong><button class="text-button" @click="backToMissionList">返回列表</button></div>
          <template v-else>
            <article class="panel mission-detail-header">
              <div><span class="panel-kicker">MISSION #{{ missionDetail.id }}</span><h2>{{ missionDetail.name }}</h2><p>创建于 {{ formatCell(missionDetail.created_at, { type: 'date' }) }} · 模型 ID {{ missionDetail.model_artifact_id || '—' }}</p></div>
              <div class="detail-actions"><span class="status-chip" :class="`status-${missionDetail.status}`">{{ missionDetail.status_label || missionDetail.status }}</span><select :value="missionDetail.status" @change="changeMissionStatus($event.target.value)"><option value="created">已创建</option><option value="ready">待调度</option><option value="planning">规划中</option><option value="running">执行中</option><option value="completed">已完成</option><option value="failed">失败</option></select></div>
            </article>
            <div class="detail-grid">
              <article class="panel detail-asset-card"><div class="panel-heading"><div><span class="panel-kicker">MISSION ASSETS</span><h2>任务文件</h2></div></div><dl class="detail-dl"><div><dt>输入图像</dt><dd>{{ missionDetail.input_image_path || '—' }}</dd></div><div><dt>识别 Mask</dt><dd>{{ missionDetail.mask_path || '尚未生成' }}</dd></div><div><dt>更新时间</dt><dd>{{ formatCell(missionDetail.updated_at, { type: 'date' }) }}</dd></div></dl></article>
              <article class="panel detail-asset-card"><div class="panel-heading"><div><span class="panel-kicker">RELATED RUNS</span><h2>仿真运行</h2></div><span class="table-note">{{ missionSimulationRuns.length }}</span></div><div v-if="!missionSimulationRuns.length" class="inline-empty">暂无关联仿真记录</div><div v-else class="related-list"><div v-for="run in missionSimulationRuns" :key="run.id"><strong>#{{ run.id }} · {{ run.planning_method_label || run.planning_method }}</strong><span>{{ run.status_label || run.status }}</span></div></div></article>
            </div>
            <article class="panel detail-task-card"><div class="panel-heading"><div><span class="panel-kicker">TASK POINTS</span><h2>关联任务点</h2></div><span class="table-note">{{ missionTaskPoints.length }}</span></div><div v-if="!missionTaskPoints.length" class="table-state compact-state"><span>∅</span><strong>该任务还没有任务点</strong><small>当前识别接口会保存 Mission，任务点需要后续任务生成流程写入。</small></div><div v-else class="real-data-table-wrap"><table class="real-data-table"><thead><tr><th>编号</th><th>灾情类别</th><th>置信度</th><th>优先级</th><th>状态</th><th>无人机</th></tr></thead><tbody><tr v-for="point in missionTaskPoints" :key="point.id"><td>#{{ point.id }}</td><td>{{ point.disaster_category_label || point.disaster_category }}</td><td>{{ formatCell(point.confidence, { type: 'percent' }) }}</td><td>{{ point.priority }}</td><td>{{ point.status_label || point.status }}</td><td>{{ point.assigned_uav_id || '—' }}</td></tr></tbody></table></div></article>
          </template>
        </section>

        <section v-else-if="activeView === 'recognition'" class="view-stack">
          <div class="recognition-toolbar"><div class="toolbar-note"><span class="pulse-dot"></span> 训练权重加载后即可离线推理</div><button class="sample-button" @click="loadSample">查看使用提示 <span>↗</span></button></div>
          <div class="recognition-layout">
            <article class="panel upload-panel">
              <div class="panel-heading"><div><span class="panel-kicker">01 / INPUT</span><h2>导入航拍图像</h2></div><span class="file-type">JPG / PNG</span></div>
              <input ref="fileInput" class="visually-hidden" type="file" accept="image/*" @change="handleFile" />
              <div class="drop-zone" :class="{ 'has-file': uploadedName }" role="button" tabindex="0" aria-label="选择航拍图像" @click="openFilePicker" @keydown.enter.prevent="openFilePicker" @keydown.space.prevent="openFilePicker" @dragover.prevent @drop.prevent="handleDrop">
                <template v-if="imagePreview"><img :src="imagePreview" alt="已上传的航拍图像" /></template>
                <template v-else>
                  <div class="aerial-preview" aria-hidden="true"><div class="preview-overlay"><span>航拍图像 / IMAGE INPUT</span><b>场景示意</b></div></div>
                  <div class="drop-copy"><strong>{{ uploadedName || '拖拽航拍图像到这里' }}</strong><small>{{ uploadedName ? '点击更换图像' : '或点击选择本地文件' }}</small></div>
                </template>
              </div>
              <div class="upload-foot"><span v-if="uploadedName" class="selected-file"><i></i>{{ uploadedName }}</span><span v-else>支持 JPG、PNG · 最大 20 MB</span><button class="text-button" @click.stop="openFilePicker">选择文件 <span>＋</span></button></div>
              <button class="wide-button" :disabled="isProcessing" @click="runRecognition">{{ isProcessing ? (uploadStage || '处理中…') : recognitionReady ? '重新运行识别' : '上传并开始识别' }} <span>→</span></button>
              <p v-if="uploadStage" class="upload-stage"><span class="loading-ring"></span>{{ uploadStage }}</p>
              <p v-if="recognitionError" class="form-error">{{ recognitionError }}</p>
            </article>

            <article class="panel result-panel">
              <div class="panel-heading"><div><span class="panel-kicker">02 / OUTPUT</span><h2>识别结果</h2></div><span class="model-chip">FloodNet · 10 类分割</span></div>
              <div class="result-preview"><template v-if="recognitionResult?.mask_url"><img class="model-mask-preview" :src="showMask ? recognitionResult.mask_url : imagePreview" alt="模型生成的语义分割 mask" /></template><div v-else class="result-blank" aria-hidden="true"><div class="result-scan-icon"><span></span></div></div><div v-if="!recognitionReady" class="result-empty"><span>◎</span><strong>等待识别输入</strong><small>选择一张航拍图，查看模型输出</small></div><div v-else class="result-overlay"><span>MASK OUTPUT</span><button @click="showMask = !showMask">{{ showMask ? '隐藏分割' : '显示分割' }}</button></div></div>
              <div v-if="recognitionClasses.length" class="classification-list"><div v-for="item in recognitionClasses" :key="item.label" class="classification-row"><span class="class-dot" :style="{ background: item.color }"></span><strong>{{ item.label }}</strong><div class="class-bar"><span :style="{ width: `${item.value * 2.1}%`, background: item.color }"></span></div><b>{{ recognitionReady ? item.confidence : '—' }}</b></div></div>
              <div v-else class="table-state compact-state"><span>∅</span><strong>尚未识别</strong><small>上传图片后显示各类别像素占比</small></div>
              <div class="result-summary"><div><span>淹水像素占比</span><strong>{{ recognitionReady ? (Number(recognitionResult?.flood_ratio || 0) * 100).toFixed(1) : '—' }}<small>%</small></strong></div><div><span>平均置信度</span><strong>{{ recognitionReady ? (Number(recognitionResult?.mean_confidence || 0) * 100).toFixed(1) : '—' }}<small>%</small></strong></div><div><span>推理耗时</span><strong>{{ recognitionReady ? (Number(recognitionResult?.inference_ms || 0) / 1000).toFixed(2) : '—' }}<small>s</small></strong></div></div>
            </article>
          </div>
          <article class="panel task-panel"><div class="panel-heading"><div><span class="panel-kicker">03 / TASK EXTRACTION</span><h2>复查任务点 <small>{{ tasks.length }} 个候选区域</small></h2></div><button class="solid-button compact" @click="openView('simulation')">进入调度 <span>→</span></button></div><div class="task-table"><div class="task-table-head"><span>任务点</span><span>灾情类型</span><span>置信度</span><span>优先级</span><span>状态</span></div><button v-for="task in tasks.slice(0, 5)" :key="task.id" class="task-row" :class="{ selected: selectedTask?.id === task.id }" @click="toggleTask(task)"><span><b>{{ task.id }}</b>{{ task.label }}</span><span>{{ task.type }}</span><span>{{ task.score }}</span><span><i class="priority-dot" :class="`priority-${task.level}`"></i>{{ task.level }}</span><span><i class="status-dot-small" :class="task.status === '已完成' ? 'is-done' : task.status === '执行中' ? 'is-running' : ''"></i>{{ task.status }}</span></button></div></article>
        </section>

        <section v-else-if="activeView === 'simulation'" class="view-stack">
          <div class="simulation-toolbar"><div class="algorithm-select"><span>当前策略</span><div class="algorithm-options"><button v-for="algorithm in ['平均分配', '最近邻', '标准 PSO', '风险加权 PSO']" :key="algorithm" :class="{ selected: selectedAlgorithm === algorithm }" @click="selectedAlgorithm = algorithm">{{ algorithm }}</button></div></div><div class="simulation-actions"><button class="outline-button" @click="resetSimulation">重置场景</button><button class="solid-button" :class="{ running: isRunning }" @click="startSimulation">{{ isRunning ? '运行中…' : '开始仿真' }} <span>{{ isRunning ? '◌' : '▶' }}</span></button></div></div><p v-if="simulationError" class="form-error simulation-error" role="alert">{{ simulationError }}</p>
          <div class="simulation-layout">
            <article class="panel map-panel"><div class="panel-heading"><div><span class="panel-kicker">LIVE MAP / 02D</span><h2>协同航线与任务态势</h2></div><div class="map-status"><i></i>{{ simulationStatus }}</div></div><div class="map-canvas" :style="{ aspectRatio: mapAspectRatio }">
  <template v-if="mapReady">
    <img class="map-image" :src="mapImageUrl" alt="航拍灾情底图" />
    <svg :viewBox="`0 0 ${imageWidth} ${imageHeight}`" preserveAspectRatio="xMidYMid meet" role="img" aria-label="多无人机调度地图">
      <g class="previous-route-layer"><path v-for="(route, uavId) in previousRoutes" :key="`${uavId}-previous-route`" :d="routePath(route)" fill="none" stroke="#d7e889" :stroke-width="Math.max(1, mapStrokeWidth / 2)" stroke-linecap="round" stroke-linejoin="round" opacity=".3" stroke-dasharray="5 8" /></g>
      <g class="route-layer">
        <path v-for="uav in uavs" :key="`${uav.id}-route`" :d="routePath(uav.route)" fill="none" :stroke="uav.color" :stroke-width="mapStrokeWidth" stroke-linecap="round" stroke-linejoin="round" :opacity="uav.status === '故障退出' ? .22 : .88" @click.stop="selectUav(uav)" />
      </g>
      <g v-for="task in tasks" :key="task.id" class="map-task" :class="{ 'task-selected': activeTask?.id === task.id }" @click.stop="toggleTask(task)">
        <circle :cx="task.x" :cy="task.y" :r="mapTaskRadius + 5" fill="#172333" stroke="#eef2dd" :stroke-width="Math.max(1, mapStrokeWidth / 2)" opacity=".95" />
        <circle :cx="task.x" :cy="task.y" :r="mapTaskRadius / 2" :fill="task.status === '已完成' ? '#78d5c5' : task.level === '高' ? '#ef8d73' : '#e4bc70'" />
        <text :x="task.x + mapTaskRadius + 6" :y="task.y + mapLabelSize / 3" fill="#fff" :font-size="mapLabelSize" stroke="#111d2a" stroke-width="3" paint-order="stroke">{{ task.id }}</text>
      </g>
      <g v-for="uav in uavs" :key="uav.id" class="uav-marker" :class="{ 'uav-failed': uav.status === '故障退出' }" :transform="`translate(${uav.x} ${uav.y})`" @click.stop="selectUav(uav)">
        <circle :r="mapTaskRadius + 5" fill="#111d2a" :stroke="uav.color" :stroke-width="mapStrokeWidth" />
        <path d="M-7 0 L0 -5 L7 0 L0 5Z" :fill="uav.color" :transform="`scale(${Math.max(1, mapTaskRadius / 10)})`" />
        <text :x="mapTaskRadius + 8" :y="mapLabelSize / 3" fill="#fff" :font-size="mapLabelSize" stroke="#111d2a" stroke-width="3" paint-order="stroke">{{ uav.id }}</text>
      </g>
      <g v-if="!tasks.length" class="map-empty-hint">
        <text :x="imageWidth / 2" :y="imageHeight / 2" text-anchor="middle" fill="#fff" :font-size="mapLabelSize * 1.4" stroke="#111d2a" stroke-width="4" paint-order="stroke">{{ dispatchNote || '未检出受淹区域' }}</text>
      </g>
      <rect v-if="!tasks.length" width="100%" height="100%" fill="transparent" @click="handleMapClick" />
    </svg>
  </template>
  <div v-else class="map-empty-state">
    <strong>等待航拍图像</strong>
    <span>完成一次灾情识别后，这里显示原图和像素航线。</span>
  </div>
  <div v-if="mapReady" class="map-image-toggle"><button type="button" @click="showMapMask = !showMapMask">{{ showMapMask && maskImageUrl ? '显示原图' : '显示 Mask' }}</button></div>
  <div class="map-scale">1 px ≈ 0.1 m（示意）</div>
  <div class="map-legend"><span><i class="legend-line teal"></i>UAV-01</span><span><i class="legend-line orange"></i>UAV-02</span><span><i class="legend-line purple"></i>UAV-03</span><span><i class="legend-point"></i>任务点</span><span v-if="Object.keys(previousRoutes).length"><i class="legend-line previous"></i>重规划前</span><span v-if="Object.keys(previousRoutes).length"><i class="legend-line current"></i>重规划后</span></div></div><div class="map-footer"><span><i class="pulse-dot"></i>同步频率 2s</span><span>坐标系 / SIM-LOCAL</span><span>任务完成 {{ completedCount }}/{{ tasks.length }}</span></div></article>
            <aside class="simulation-side">
  <article v-if="selectedTask || selectedUav" class="panel selection-panel">
    <div v-if="selectedTask" class="selection-block">
      <div class="panel-heading"><div><span class="panel-kicker">TASK DETAIL</span><h2>{{ selectedTask.label || selectedTask.id }}</h2></div><span class="status-chip">{{ selectedTask.source === 'manual' ? '手动' : selectedTask.status }}</span></div>
      <dl class="selection-dl"><div><dt>类别</dt><dd>{{ selectedTask.type }}</dd></div><div><dt>像素占比</dt><dd>{{ (Number(selectedTask.areaRatio || 0) * 100).toFixed(3) }}%</dd></div><div><dt>置信度</dt><dd>{{ (Number(selectedTask.score || 0) * 100).toFixed(1) }}%</dd></div><div><dt>优先级</dt><dd>{{ selectedTask.priority }}</dd></div></dl>
    </div>
    <div v-if="selectedUav" class="selection-block">
      <div class="panel-heading"><div><span class="panel-kicker">ROUTE DETAIL</span><h2>{{ selectedUav.id }}</h2></div><span class="status-chip">{{ selectedUav.status }}</span></div>
      <dl class="selection-dl"><div><dt>分配任务</dt><dd>{{ selectedUav.assigned }}</dd></div><div><dt>当前航程</dt><dd>{{ routeLength(selectedUav.route).toFixed(1) }} px</dd></div><div><dt>当前位置</dt><dd>{{ Math.round(selectedUav.x) }}, {{ Math.round(selectedUav.y) }}</dd></div></dl>
    </div>
  </article><article class="panel uav-panel"><div class="panel-heading"><div><span class="panel-kicker">FLEET STATUS</span><h2>机队状态</h2></div><span class="count-label">{{ uavs.length }} AIRCRAFT</span></div><div class="uav-list"><div v-for="uav in uavs" :key="uav.id" class="uav-card" :class="{ failed: uav.status === '故障退出' }"><div class="uav-card-top"><span class="uav-color" :style="{ background: uav.color }"></span><div><strong>{{ uav.id }}</strong><small>{{ uav.name }}</small></div><span class="uav-state">{{ uav.status }}</span></div><div class="battery-row"><span>电量</span><div class="battery-track"><i :style="{ width: `${uav.battery}%`, background: uav.color }"></i></div><b>{{ uav.battery }}%</b></div><div class="uav-meta"><span>分配任务 <b>{{ uav.assigned }}</b></span><span>返航余量 <b>{{ Math.max(10, uav.battery - 18) }}%</b></span></div></div></div></article><article class="panel event-panel simulation-events"><div class="panel-heading"><div><span class="panel-kicker">EVENT INJECTION</span><h2>事件模拟</h2></div><span class="event-help">用于演示</span></div><div class="event-buttons"><button @click="triggerEvent('故障')"><span class="event-button-icon danger">×</span><div><strong>UAV-02 故障</strong><small>模拟退出并重规划</small></div><span>→</span></button><button @click="triggerEvent('新增')"><span class="event-button-icon add">＋</span><div><strong>新增复查任务</strong><small>生成增量航线</small></div><span>→</span></button></div></article></aside>
          </div>
          <div class="simulation-metrics"><article class="metric-card"><span>仿真进度</span><strong>{{ progressLabel }}</strong><div class="metric-progress"><i :style="{ width: `${simulationProgress}%` }"></i></div></article><article class="metric-card"><span>重点任务完成率</span><strong>{{ plannerCompletionLabel }}</strong><em>{{ simulationPlan ? '当前计划' : '等待计划' }}</em></article><article class="metric-card"><span>已规划总航程</span><strong>{{ plannerDistanceLabel }}</strong><em>{{ simulationPlan ? '二维仿真距离' : '等待计划' }}</em></article><article class="metric-card"><span>预计完成时间</span><strong>{{ plannerTimeLabel }}</strong><em>{{ simulationPlan ? '当前计划 makespan' : '等待计划' }}</em></article></div>
        </section>

        <section v-else-if="activeView === 'task_points'" class="view-stack">
          <div class="data-view-toolbar"><div class="data-view-context"><span class="database-pulse"></span><span>TASK POINTS</span><b>灾情区域和复查优先级</b></div><button class="outline-button" :disabled="taskPointLoading" @click="loadTaskPointList">{{ taskPointLoading ? '读取中…' : '刷新任务点' }} <span>↻</span></button></div>
          <article class="panel task-point-list-panel">
            <div class="panel-heading"><div><span class="panel-kicker">MISSION CENTER / TASK POINTS</span><h2>任务点台账</h2></div><span class="table-note">{{ taskPointCount }} RECORDS</span></div>
            <div class="resource-filter-row"><label>灾情类别<select v-model="taskPointCategoryFilter" @change="loadTaskPointList"><option value="">全部类别</option><option v-for="item in disasterCategoryOptions" :key="item.value" :value="item.value">{{ item.label }}（{{ item.count }}）</option></select></label><label>任务状态<select v-model="taskPointStatusFilter" @change="loadTaskPointList"><option value="">全部状态</option><option value="pending">待复查</option><option value="assigned">已分配</option><option value="in_progress">执行中</option><option value="completed">已完成</option><option value="cancelled">已取消</option></select></label></div>
            <div v-if="taskPointLoading" class="table-state"><span class="loading-ring"></span><strong>正在读取任务点…</strong></div>
            <div v-else-if="taskPointError" class="table-state table-error"><span>!</span><strong>{{ taskPointError }}</strong><button class="text-button" @click="loadTaskPointList">重试 <span>↻</span></button></div>
            <div v-else-if="!taskPointRows.length" class="table-state"><span>∅</span><strong>暂无任务点数据</strong><small>识别结果生成任务点后，数据会显示在这里。</small></div>
            <div v-else class="real-data-table-wrap"><table class="real-data-table"><thead><tr><th>编号</th><th>任务 ID</th><th>灾情类别</th><th>坐标</th><th>面积</th><th>置信度</th><th>优先级</th><th>状态</th></tr></thead><tbody><tr v-for="point in taskPointRows" :key="point.id" class="clickable-row" @click="openMissionDetail(point.mission_id)"><td>#{{ point.id }}</td><td>#{{ point.mission_id }}</td><td>{{ point.disaster_category_label || point.disaster_category }}</td><td>({{ point.coordinate_x }}, {{ point.coordinate_y }})</td><td>{{ point.area }}</td><td>{{ formatCell(point.confidence, { type: 'percent' }) }}</td><td class="cell-emphasis">{{ point.priority }}</td><td>{{ point.status_label || point.status }}</td></tr></tbody></table></div>
          </article>
        </section>

        <section v-else-if="isDataView" class="view-stack">
          <div class="data-view-toolbar">
            <div class="data-view-context"><span class="database-pulse"></span><span>DATABASE / SQLITE</span><b>实时读取当前项目数据</b></div>
            <button class="outline-button" :disabled="tableLoading" @click="loadDataView()">{{ tableLoading ? '读取中…' : '刷新数据' }} <span>↻</span></button>
          </div>
          <div class="data-summary-row"><div class="data-count-card"><span>当前表记录</span><strong>{{ tableCount }}</strong><small>{{ currentTable.title }}</small></div><div class="data-summary-copy"><span class="panel-kicker">LIVE TABLE VIEW</span><h2>{{ currentTable.title }}</h2><p>{{ currentTable.description }} 所有记录直接来自 Django ORM API。</p></div><div class="data-source-badge"><span>SOURCE</span><strong>/api{{ currentTable.endpoint }}</strong></div></div>
          <article class="panel data-table-panel"><div class="panel-heading"><div><span class="panel-kicker">{{ currentTable.eyebrow }}</span><h2>真实数据列表</h2></div><span class="table-note">{{ tableCount }} RECORDS</span></div><div v-if="tableLoading" class="table-state"><span class="loading-ring"></span><strong>正在读取数据库…</strong></div><div v-else-if="tableError" class="table-state table-error"><span>!</span><strong>{{ tableError }}</strong><button class="text-button" @click="loadDataView()">重试 <span>↻</span></button></div><div v-else-if="!tableRows.length" class="table-state"><span>∅</span><strong>当前数据表暂无记录</strong><small>通过对应 POST API 新增数据后，点击刷新即可查看。</small></div><div v-else class="real-data-table-wrap"><table class="real-data-table"><thead><tr><th v-for="column in currentTable.columns" :key="column.key">{{ column.label }}</th></tr></thead><tbody><tr v-for="(row, rowIndex) in tableRows" :key="row.id || rowIndex"><td v-for="column in currentTable.columns" :key="column.key" :class="{ 'cell-emphasis': column.key === 'name' || column.key === 'identifier' || column.key === 'priority' }">{{ formatCell(row[column.key], column) }}</td></tr></tbody></table></div></article>
        </section>
      </div>
    </main>
  </div>
</template>

