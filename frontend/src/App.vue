<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

import { fetchCollection, recognizeImage } from './api/client'

const activeView = ref('overview')
const selectedAlgorithm = ref('风险加权 PSO')
const selectedTask = ref(null)
const uploadedName = ref('')
const imagePreview = ref('')
const selectedFile = ref(null)
const recognitionResult = ref(null)
const recognitionError = ref('')
const recognitionReady = ref(false)
const isProcessing = ref(false)
const showMask = ref(true)
const fileInput = ref(null)
const isRunning = ref(false)
const simulationProgress = ref(72)
const simulationStatus = ref('已完成首轮规划')
const simulationTimer = ref(null)
const failedUav = ref('')
const dataMenuOpen = ref(true)
const activeDataGroup = ref('data-assets')
const tableRows = ref([])
const tableCount = ref(0)
const tableLoading = ref(false)
const tableError = ref('')

const navItems = [
  { id: 'overview', label: '总览', index: '01' },
  { id: 'recognition', label: '灾情识别', index: '02', badge: 'AI' },
  { id: 'simulation', label: '调度仿真', index: '03' },
  { id: 'experiments', label: '实验对比', index: '04' },
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
  simulation: { eyebrow: 'SWARM SIMULATION', title: '调度仿真', description: '在二维地图中观察任务分配、航线执行与动态重规划。' },
  experiments: { eyebrow: 'BENCHMARK LAB', title: '实验对比', description: '用统一任务和随机种子比较不同调度策略。' },
}

const tasks = ref([
  { id: 'T-001', label: '北侧居民区', type: '受淹建筑', level: '高', score: 0.96, status: '待复查', x: 160, y: 120 },
  { id: 'T-002', label: '东侧主干道', type: '受淹道路', level: '高', score: 0.91, status: '执行中', x: 350, y: 88 },
  { id: 'T-003', label: '南侧农田', type: '水体', level: '中', score: 0.84, status: '已完成', x: 520, y: 260 },
  { id: 'T-004', label: '西侧桥梁', type: '受淹道路', level: '高', score: 0.89, status: '待复查', x: 240, y: 310 },
  { id: 'T-005', label: '河道拐点', type: '水体', level: '中', score: 0.78, status: '待复查', x: 580, y: 126 },
  { id: 'T-006', label: '南部仓储区', type: '受淹建筑', level: '中', score: 0.82, status: '已完成', x: 430, y: 345 },
])

const defaultUavs = [
  { id: 'UAV-01', name: '侦察一号', color: '#78d5c5', battery: 82, status: '执行中', assigned: 2, x: 118, y: 220, route: [[118, 220], [160, 120], [350, 88]] },
  { id: 'UAV-02', name: '侦察二号', color: '#e4bc70', battery: 64, status: '执行中', assigned: 2, x: 380, y: 190, route: [[380, 190], [240, 310], [430, 345]] },
  { id: 'UAV-03', name: '侦察三号', color: '#9b9cf8', battery: 91, status: '待命', assigned: 2, x: 628, y: 330, route: [[628, 330], [520, 260], [580, 126]] },
]
const uavs = ref(cloneUavs(defaultUavs))

const recognitionClasses = ref([
  { label: '受淹建筑', value: 28, confidence: '96.2%', color: '#ef8d73' },
  { label: '受淹道路', value: 41, confidence: '91.4%', color: '#e4bc70' },
  { label: '水体区域', value: 19, confidence: '87.8%', color: '#78d5c5' },
  { label: '未受影响', value: 12, confidence: '98.1%', color: '#6c768d' },
])

const experiments = [
  { method: '平均分配', tag: 'BASELINE', completion: 68, time: '18:42', distance: '4.86 km', recovery: '—', tone: 'muted' },
  { method: '最近任务优先', tag: 'GREEDY', completion: 76, time: '16:20', distance: '4.21 km', recovery: '62%', tone: 'blue' },
  { method: '标准离散 PSO', tag: 'PSO', completion: 86, time: '13:58', distance: '3.64 km', recovery: '78%', tone: 'purple' },
  { method: '风险加权 PSO', tag: 'PROPOSED', completion: 94, time: '11:26', distance: '3.18 km', recovery: '93%', tone: 'lime' },
]

const eventLog = ref([
  { time: '刚刚', title: '规划任务已生成', detail: '6 个任务点 · 3 架虚拟无人机', tone: 'success' },
  { time: '01:42', title: 'UAV-01 抵达北侧居民区', detail: '高优先级任务完成', tone: 'teal' },
  { time: '02:18', title: '识别结果已同步', detail: 'FloodNet · 512 × 512', tone: 'purple' },
])

const isDataView = computed(() => Boolean(dataTableConfigs[activeView.value]))
const currentMeta = computed(() => viewMeta[activeView.value] || dataTableConfigs[activeView.value] || viewMeta.overview)
const currentTable = computed(() => dataTableConfigs[activeView.value])
const completedCount = computed(() => tasks.value.filter((task) => task.status === '已完成').length)
const progressLabel = computed(() => `${Math.round(simulationProgress.value)}%`)
const activeTask = computed(() => selectedTask.value || tasks.value[0])
const stats = computed(() => [
  { label: '识别置信度', value: recognitionReady.value ? `${((recognitionResult.value?.mean_confidence || 0) * 100).toFixed(1)}%` : '—', delta: recognitionReady.value ? `${recognitionResult.value?.device || 'CPU'} 推理` : '等待输入', icon: '◎', tone: 'teal' },
  { label: '复查任务点', value: `${tasks.value.length}`, delta: `${completedCount.value} 已完成`, icon: '⌖', tone: 'orange' },
  { label: '重点任务完成率', value: `${experiments[3].completion}%`, delta: '风险加权 PSO', icon: '↗', tone: 'purple' },
  { label: '预计总航程', value: '3.18 km', delta: '较基线 -34.6%', icon: '⌁', tone: 'lime' },
])

function cloneUavs(source) {
  return source.map((uav) => ({ ...uav, route: uav.route.map((point) => [...point]) }))
}

function routePath(route) {
  return route.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point[0]} ${point[1]}`).join(' ')
}

function openView(view) {
  activeView.value = view
  if (dataTableConfigs[view]) loadDataView(view)
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
  if (!file || !file.type.startsWith('image/')) return
  selectedFile.value = file
  uploadedName.value = file.name
  recognitionReady.value = false
  recognitionResult.value = null
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
  recognitionError.value = ''
  try {
    const result = await recognizeImage(selectedFile.value)
    recognitionResult.value = result
    const colors = ['#6c768d', '#ef8d73', '#9aa0a8', '#e4bc70', '#9aa0a8', '#78d5c5', '#70a674', '#9b9cf8', '#5ba6de', '#9ab267']
    recognitionClasses.value = (result.class_stats || []).map((item) => ({
      label: item.label,
      value: Math.max(0, Math.min(100, Number(item.ratio || 0) * 100)),
      confidence: `${(Number(item.confidence || 0) * 100).toFixed(1)}%`,
      color: colors[item.id] || '#6c768d',
    })).filter((item) => item.value > 0)
    recognitionReady.value = true
    eventLog.value.unshift({ time: '刚刚', title: '模型识别完成', detail: `Mission #${result.mission_id} · ${result.inference_ms} ms`, tone: 'success' })
  } catch (error) {
    recognitionError.value = error.message || '模型识别失败。'
    recognitionReady.value = false
  } finally {
    isProcessing.value = false
  }
}

function toggleTask(task) {
  selectedTask.value = selectedTask.value?.id === task.id ? null : task
}

function startSimulation() {
  if (isRunning.value) return
  isRunning.value = true
  simulationStatus.value = '仿真运行中'
  simulationProgress.value = Math.max(8, simulationProgress.value > 95 ? 8 : simulationProgress.value)
  clearInterval(simulationTimer.value)
  simulationTimer.value = window.setInterval(() => {
    simulationProgress.value += 8
    if (simulationProgress.value >= 100) {
      simulationProgress.value = 100
      isRunning.value = false
      simulationStatus.value = '仿真已完成'
      clearInterval(simulationTimer.value)
      eventLog.value.unshift({ time: '刚刚', title: '仿真运行完成', detail: `${selectedAlgorithm.value} · 6 个任务点`, tone: 'success' })
    }
  }, 220)
}

function triggerEvent(type) {
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
  } else {
    simulationStatus.value = '新增任务等待分配'
    eventLog.value.unshift({ time: '刚刚', title: '新增 2 个复查任务', detail: '调度器正在计算最短增量航线', tone: 'orange' })
  }
}

function resetSimulation() {
  clearInterval(simulationTimer.value)
  isRunning.value = false
  failedUav.value = ''
  simulationProgress.value = 72
  simulationStatus.value = '已完成首轮规划'
  uavs.value = cloneUavs(defaultUavs)
  eventLog.value = [{ time: '刚刚', title: '规划任务已生成', detail: '6 个任务点 · 3 架虚拟无人机', tone: 'success' }]
}

function downloadReport() {
  const header = 'method,completion_rate,total_time,total_distance,recovery_rate\n'
  const rows = experiments.map((item) => `${item.method},${item.completion}%,${item.time},${item.distance},${item.recovery}`).join('\n')
  const blob = new Blob([`\ufeff${header}${rows}`], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'xunxunzhicun-experiment-report.csv'
  link.click()
  URL.revokeObjectURL(url)
}

onUnmounted(() => {
  clearInterval(simulationTimer.value)
  if (imagePreview.value) URL.revokeObjectURL(imagePreview.value)
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
        <button v-for="item in navItems" :key="item.id" class="nav-item" :class="{ active: activeView === item.id }" @click="openView(item.id)">
          <span class="nav-index">{{ item.index }}</span>
          <span class="nav-label">{{ item.label }}</span>
          <span v-if="item.badge" class="nav-badge">{{ item.badge }}</span>
          <span v-else class="nav-arrow">↗</span>
        </button>
      </nav>

      <div class="backend-nav">
        <button class="backend-nav-title" :class="{ active: isDataView }" @click="dataMenuOpen = !dataMenuOpen">
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
        <span class="status-dot"></span>
        <div><strong>系统运行正常</strong><small>模型服务按需加载</small></div>
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
          <div class="live-pill"><span></span> LIVE DEMO</div>
          <button class="icon-button" title="帮助">?</button>
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
          <button class="outline-button" @click="downloadReport">导出实验报告 <span>↓</span></button>
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
              <div class="visual-grid"></div>
              <div class="radar-ring ring-a"></div><div class="radar-ring ring-b"></div><div class="radar-ring ring-c"></div>
              <div class="radar-sweep"></div>
              <span class="radar-dot dot-a"></span><span class="radar-dot dot-b"></span><span class="radar-dot dot-c"></span>
              <span class="visual-caption">MULTI-UAV / 03</span>
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
              <div class="mission-summary">
                <div class="mission-map mini-map"><span class="mini-route route-one"></span><span class="mini-route route-two"></span><i class="mini-point p-one"></i><i class="mini-point p-two"></i><i class="mini-point p-three"></i></div>
                <div class="mission-info"><div class="mission-title"><strong>洪涝灾情复查 · 0217</strong><span class="success-tag">已完成 72%</span></div><p>FloodNet / 东部试验区 / 6 个复查任务点</p><div class="progress-track"><span style="width: 72%"></span></div><div class="mission-foot"><span>3 架无人机</span><span>运行 08:42</span><span>风险加权 PSO</span></div></div>
              </div>
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

        <section v-else-if="activeView === 'recognition'" class="view-stack">
          <div class="recognition-toolbar"><div class="toolbar-note"><span class="pulse-dot"></span> 训练权重加载后即可离线推理</div><button class="sample-button" @click="loadSample">查看使用提示 <span>↗</span></button></div>
          <div class="recognition-layout">
            <article class="panel upload-panel">
              <div class="panel-heading"><div><span class="panel-kicker">01 / INPUT</span><h2>导入航拍图像</h2></div><span class="file-type">JPG / PNG</span></div>
              <input ref="fileInput" class="visually-hidden" type="file" accept="image/*" @change="handleFile" />
              <div class="drop-zone" :class="{ 'has-file': uploadedName }" @click="openFilePicker" @dragover.prevent @drop.prevent="handleDrop">
                <template v-if="imagePreview"><img :src="imagePreview" alt="已上传的航拍图像" /></template>
                <template v-else>
                  <div class="aerial-preview"><svg viewBox="0 0 520 300" role="img" aria-label="航拍样例图"><defs><pattern id="fieldGrid" width="34" height="34" patternUnits="userSpaceOnUse"><rect width="34" height="34" fill="#1e2a39"/><path d="M 34 0 L 0 0 0 34" fill="none" stroke="#324558" stroke-width="1"/></pattern></defs><rect width="520" height="300" fill="url(#fieldGrid)"/><path d="M0 212 C90 175 118 232 196 192 S324 162 402 194 S470 202 520 168 V300 H0Z" fill="#224d55" opacity=".8"/><path d="M86 0 L130 300 M286 0 L260 300 M438 0 L392 300" stroke="#7d8e73" stroke-width="18" opacity=".45"/><path d="M86 0 L130 300 M286 0 L260 300 M438 0 L392 300" stroke="#d1c68d" stroke-width="2" stroke-dasharray="7 9" opacity=".8"/><path d="M210 40 L380 58 L368 148 L205 131Z M80 60 L180 72 L170 138 L70 126Z M308 214 L465 230 L454 280 L300 266Z" fill="#db826b" opacity=".65"/><circle cx="140" cy="104" r="32" fill="none" stroke="#f2c879" stroke-width="2" stroke-dasharray="5 5"/><circle cx="350" cy="104" r="38" fill="none" stroke="#78d5c5" stroke-width="2" stroke-dasharray="5 5"/></svg><div class="preview-overlay"><span>FLOODNET / SAMPLE</span><b>512 × 512</b></div></div>
                  <div class="drop-copy"><strong>{{ uploadedName || '拖拽航拍图像到这里' }}</strong><small>{{ uploadedName ? '点击更换图像' : '或点击选择本地文件' }}</small></div>
                </template>
              </div>
              <div class="upload-foot"><span v-if="uploadedName" class="selected-file"><i></i>{{ uploadedName }}</span><span v-else>支持 JPG、PNG · 最大 20 MB</span><button class="text-button" @click.stop="openFilePicker">选择文件 <span>＋</span></button></div>
              <button class="wide-button" :disabled="isProcessing" @click="runRecognition">{{ isProcessing ? '模型推理中…' : recognitionReady ? '重新运行识别' : '开始识别' }} <span>→</span></button>
              <p v-if="recognitionError" class="form-error">{{ recognitionError }}</p>
            </article>

            <article class="panel result-panel">
              <div class="panel-heading"><div><span class="panel-kicker">02 / OUTPUT</span><h2>识别结果</h2></div><span class="model-chip">FloodNet · 10 类分割</span></div>
              <div class="result-preview"><template v-if="recognitionResult?.mask_url"><img class="model-mask-preview" :src="showMask ? recognitionResult.mask_url : imagePreview" alt="模型生成的语义分割 mask" /></template><svg v-else viewBox="0 0 640 280" role="img" aria-label="识别结果预览"><defs><pattern id="resultGrid" width="32" height="32" patternUnits="userSpaceOnUse"><rect width="32" height="32" fill="#172333"/><path d="M 32 0 L 0 0 0 32" fill="none" stroke="#2c4152" stroke-width="1"/></pattern></defs><rect width="640" height="280" fill="url(#resultGrid)"/><path d="M0 205 C100 170 172 234 265 185 S426 163 520 206 S590 192 640 178 V280 H0Z" fill="#1d4b54"/><path d="M80 18 L126 280 M350 0 L312 280 M544 0 L488 280" stroke="#83916f" stroke-width="22" opacity=".4"/><path d="M80 18 L126 280 M350 0 L312 280 M544 0 L488 280" stroke="#d3ca94" stroke-width="2" stroke-dasharray="8 10"/><g v-if="showMask" opacity=".88"><path d="M168 32 L325 48 L308 126 L164 113Z" fill="#ee8f76"/><path d="M354 171 L506 188 L493 251 L340 240Z" fill="#e4bc70"/><path d="M54 170 L138 150 L163 214 L72 234Z" fill="#78d5c5"/></g><g v-if="recognitionReady" class="result-markers"><circle cx="245" cy="84" r="6" fill="#fff"/><circle cx="430" cy="214" r="6" fill="#fff"/><circle cx="102" cy="192" r="6" fill="#fff"/></g></svg><div v-if="!recognitionReady" class="result-empty"><span>◎</span><strong>等待识别输入</strong><small>选择一张航拍图，查看模型输出</small></div><div v-else class="result-overlay"><span>MASK OUTPUT</span><button @click="showMask = !showMask">{{ showMask ? '隐藏分割' : '显示分割' }}</button></div></div>
              <div class="classification-list"><div v-for="item in recognitionClasses" :key="item.label" class="classification-row"><span class="class-dot" :style="{ background: item.color }"></span><strong>{{ item.label }}</strong><div class="class-bar"><span :style="{ width: `${item.value * 2.1}%`, background: item.color }"></span></div><b>{{ recognitionReady ? item.confidence : '—' }}</b></div></div>
              <div class="result-summary"><div><span>淹水像素占比</span><strong>{{ recognitionReady ? (Number(recognitionResult?.flood_ratio || 0) * 100).toFixed(1) : '—' }}<small>%</small></strong></div><div><span>平均置信度</span><strong>{{ recognitionReady ? (Number(recognitionResult?.mean_confidence || 0) * 100).toFixed(1) : '—' }}<small>%</small></strong></div><div><span>推理耗时</span><strong>{{ recognitionReady ? (Number(recognitionResult?.inference_ms || 0) / 1000).toFixed(2) : '—' }}<small>s</small></strong></div></div>
            </article>
          </div>
          <article class="panel task-panel"><div class="panel-heading"><div><span class="panel-kicker">03 / TASK EXTRACTION</span><h2>复查任务点 <small>{{ tasks.length }} 个候选区域</small></h2></div><button class="solid-button compact" @click="openView('simulation')">进入调度 <span>→</span></button></div><div class="task-table"><div class="task-table-head"><span>任务点</span><span>灾情类型</span><span>置信度</span><span>优先级</span><span>状态</span></div><button v-for="task in tasks.slice(0, 5)" :key="task.id" class="task-row" :class="{ selected: selectedTask?.id === task.id }" @click="toggleTask(task)"><span><b>{{ task.id }}</b>{{ task.label }}</span><span>{{ task.type }}</span><span>{{ task.score }}</span><span><i class="priority-dot" :class="`priority-${task.level}`"></i>{{ task.level }}</span><span><i class="status-dot-small" :class="task.status === '已完成' ? 'is-done' : task.status === '执行中' ? 'is-running' : ''"></i>{{ task.status }}</span></button></div></article>
        </section>

        <section v-else-if="activeView === 'simulation'" class="view-stack">
          <div class="simulation-toolbar"><div class="algorithm-select"><span>当前策略</span><div class="algorithm-options"><button v-for="algorithm in ['最近邻', '标准 PSO', '风险加权 PSO']" :key="algorithm" :class="{ selected: selectedAlgorithm === algorithm }" @click="selectedAlgorithm = algorithm">{{ algorithm }}</button></div></div><div class="simulation-actions"><button class="outline-button" @click="resetSimulation">重置场景</button><button class="solid-button" :class="{ running: isRunning }" @click="startSimulation">{{ isRunning ? '运行中…' : '开始仿真' }} <span>{{ isRunning ? '◌' : '▶' }}</span></button></div></div>
          <div class="simulation-layout">
            <article class="panel map-panel"><div class="panel-heading"><div><span class="panel-kicker">LIVE MAP / 02D</span><h2>协同航线与任务态势</h2></div><div class="map-status"><i></i>{{ simulationStatus }}</div></div><div class="map-canvas"><svg viewBox="0 0 760 420" role="img" aria-label="多无人机调度地图"><defs><pattern id="mapGrid" width="38" height="38" patternUnits="userSpaceOnUse"><rect width="38" height="38" fill="#111d2a"/><path d="M 38 0 L 0 0 0 38" fill="none" stroke="#203243" stroke-width="1"/></pattern></defs><rect width="760" height="420" fill="url(#mapGrid)"/><path d="M0 130 C120 90 210 180 310 138 S510 88 760 134" fill="none" stroke="#2c5260" stroke-width="58" opacity=".32"/><path d="M0 130 C120 90 210 180 310 138 S510 88 760 134" fill="none" stroke="#426a72" stroke-width="2" stroke-dasharray="9 9" opacity=".65"/><path d="M18 350 C150 298 210 354 330 310 S540 302 742 350" fill="none" stroke="#344d5b" stroke-width="34" opacity=".4"/><g class="route-layer"><path v-for="uav in uavs" :key="`${uav.id}-route`" :d="routePath(uav.route)" fill="none" :stroke="uav.color" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" :opacity="uav.status === '故障退出' ? .22 : .88" stroke-dasharray="7 5"/></g><g v-for="task in tasks" :key="task.id" class="map-task" :class="{ 'task-selected': activeTask.id === task.id }" @click="toggleTask(task)"><circle :cx="task.x" :cy="task.y" r="13" fill="#172333" stroke="#eef2dd" stroke-width="1" opacity=".95"/><circle :cx="task.x" :cy="task.y" r="5" :fill="task.status === '已完成' ? '#78d5c5' : task.level === '高' ? '#ef8d73' : '#e4bc70'"/><text :x="task.x + 18" :y="task.y + 4" fill="#aab7b1" font-size="11">{{ task.id }}</text></g><g v-for="uav in uavs" :key="uav.id" class="uav-marker" :class="{ 'uav-failed': uav.status === '故障退出' }" :transform="`translate(${uav.x} ${uav.y})`"><circle r="18" fill="#111d2a" :stroke="uav.color" stroke-width="2"/><path d="M-7 0 L0 -5 L7 0 L0 5Z" :fill="uav.color"/><text x="22" y="4" fill="#edf0e4" font-size="11">{{ uav.id }}</text></g></svg><div class="map-scale">0 —— 100m</div><div class="map-legend"><span><i class="legend-line teal"></i>UAV-01</span><span><i class="legend-line orange"></i>UAV-02</span><span><i class="legend-line purple"></i>UAV-03</span><span><i class="legend-point"></i>任务点</span></div></div><div class="map-footer"><span><i class="pulse-dot"></i>同步频率 2s</span><span>坐标系 / SIM-LOCAL</span><span>任务完成 {{ completedCount }}/{{ tasks.length }}</span></div></article>
            <aside class="simulation-side"><article class="panel uav-panel"><div class="panel-heading"><div><span class="panel-kicker">FLEET STATUS</span><h2>机队状态</h2></div><span class="count-label">{{ uavs.length }} AIRCRAFT</span></div><div class="uav-list"><div v-for="uav in uavs" :key="uav.id" class="uav-card" :class="{ failed: uav.status === '故障退出' }"><div class="uav-card-top"><span class="uav-color" :style="{ background: uav.color }"></span><div><strong>{{ uav.id }}</strong><small>{{ uav.name }}</small></div><span class="uav-state">{{ uav.status }}</span></div><div class="battery-row"><span>电量</span><div class="battery-track"><i :style="{ width: `${uav.battery}%`, background: uav.color }"></i></div><b>{{ uav.battery }}%</b></div><div class="uav-meta"><span>分配任务 <b>{{ uav.assigned }}</b></span><span>返航余量 <b>{{ Math.max(10, uav.battery - 18) }}%</b></span></div></div></div></article><article class="panel event-panel simulation-events"><div class="panel-heading"><div><span class="panel-kicker">EVENT INJECTION</span><h2>事件模拟</h2></div><span class="event-help">用于演示</span></div><div class="event-buttons"><button @click="triggerEvent('故障')"><span class="event-button-icon danger">×</span><div><strong>UAV-02 故障</strong><small>模拟退出并重规划</small></div><span>→</span></button><button @click="triggerEvent('新增')"><span class="event-button-icon add">＋</span><div><strong>新增复查任务</strong><small>生成增量航线</small></div><span>→</span></button></div></article></aside>
          </div>
          <div class="simulation-metrics"><article class="metric-card"><span>仿真进度</span><strong>{{ progressLabel }}</strong><div class="metric-progress"><i :style="{ width: `${simulationProgress}%` }"></i></div></article><article class="metric-card"><span>重点任务完成率</span><strong>94<small>%</small></strong><em>+18.2% <small>vs baseline</small></em></article><article class="metric-card"><span>已规划总航程</span><strong>3.18<small>km</small></strong><em>−34.6% <small>vs baseline</small></em></article><article class="metric-card"><span>预计完成时间</span><strong>11:26</strong><em>−38.4% <small>vs baseline</small></em></article></div>
        </section>

        <section v-else-if="activeView === 'experiments'" class="view-stack">
          <div class="experiment-summary"><div><span class="panel-kicker">CONTROLLED EXPERIMENT</span><h2>同一任务，不同策略</h2><p>所有方案使用相同任务点、初始电量和故障事件，比较调度算法在效率与恢复能力上的差异。</p></div><button class="solid-button" @click="downloadReport">下载 CSV 报告 <span>↓</span></button></div>
          <div class="experiment-cards"><article v-for="item in experiments" :key="item.method" class="experiment-card" :class="`experiment-${item.tone}`"><div class="experiment-card-top"><span>{{ item.tag }}</span><i v-if="item.tone === 'lime'">PROPOSED</i></div><strong>{{ item.completion }}<small>%</small></strong><span>重点任务完成率</span><div class="experiment-bar"><i :style="{ width: `${item.completion}%` }"></i></div><p>{{ item.method }}</p></article></div>
          <article class="panel comparison-panel"><div class="panel-heading"><div><span class="panel-kicker">BENCHMARK TABLE</span><h2>调度结果对比</h2></div><span class="table-note">同一仿真场景 / N = 30</span></div><div class="comparison-table"><div class="comparison-head"><span>方法</span><span>重点任务完成率</span><span>总完成时间</span><span>总航程</span><span>故障恢复率</span></div><div v-for="item in experiments" :key="`${item.method}-row`" class="comparison-row"><span><i :class="`method-dot ${item.tone}`"></i><strong>{{ item.method }}</strong><small>{{ item.tag }}</small></span><span><b>{{ item.completion }}%</b><div class="table-bar"><i :class="item.tone" :style="{ width: `${item.completion}%` }"></i></div></span><span>{{ item.time }}</span><span>{{ item.distance }}</span><span :class="{ 'highlight-value': item.tone === 'lime' }">{{ item.recovery }}</span></div></div></article>
          <div class="ablation-grid"><article class="panel ablation-card"><div class="panel-heading"><div><span class="panel-kicker">ABLATION 01</span><h2>移除不确定性评分</h2></div><span class="loss-tag">−12.4%</span></div><p>没有识别置信度作为优先级因素时，高风险区域的发现顺序变慢。</p><div class="ablation-chart"><span style="height: 48%"></span><span style="height: 64%"></span><span style="height: 56%"></span><span style="height: 76%"></span><span style="height: 68%"></span><span style="height: 84%"></span></div><div class="chart-labels"><span>完成时间</span><span>高优任务率</span><span>恢复率</span></div></article><article class="panel ablation-card"><div class="panel-heading"><div><span class="panel-kicker">ABLATION 02</span><h2>移除动态重调度</h2></div><span class="loss-tag">−18.7%</span></div><p>故障发生后保留静态分配，会造成剩余无人机闲置和任务延误。</p><div class="ablation-chart purple-chart"><span style="height: 70%"></span><span style="height: 42%"></span><span style="height: 61%"></span><span style="height: 34%"></span><span style="height: 51%"></span><span style="height: 27%"></span></div><div class="chart-labels"><span>完成时间</span><span>高优任务率</span><span>恢复率</span></div></article></div>
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

