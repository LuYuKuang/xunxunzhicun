# 汛巡智群项目 Agent 规范

## 项目定位

本项目的目标是实现“汛巡智群——基于模式识别与机器学习的航拍灾情识别、多无人机协同复查与动态调度软件”。它是一款面向灾后巡检的纯软件作品：使用模式识别和机器学习方法分析无人机航拍图像，识别受淹道路、受淹建筑和水体，将识别结果转换为复查任务，再为多架虚拟无人机分配任务、规划路线，并在故障或低电量时重新调度。

项目服务于“挑战杯”科技发明制作 B 类方向。作品应突出可运行的软件系统、清晰的研究问题和可复现实验结果。当前版本只做二维仿真，不连接真实飞控、GPS、在线通信或硬件设备。

## 当前工程状态

- 后端：Django 6.1.2，项目包为 `drone`，业务应用为 `core`。
- 管理后台：`django-simpleui`，语言设置为 `zh-hans`。
- 前端：Vue 3 + Vite，位于 `frontend/`。
- 机器学习：以 PyTorch 为主，结合 OpenCV、NumPy 和 scikit-learn 完成数据处理、特征工程、训练和评估。
- Django 开发服务：`http://127.0.0.1:8000/`。
- Vue 开发服务：`http://127.0.0.1:5173/`。
- Django 根路径目前重定向到 Vue 首页，`/admin/` 保留为 SimpleUI 管理后台。
- Vite 已将 `/api`、`/admin`、`/static` 和 `/media` 代理到 Django 8000 端口。
- Python 虚拟环境：`.venv/`；Python 版本为 3.12.5。
- 数据库：当前使用项目根目录的 SQLite 文件 `db.sqlite3`，已用于 Django 用户、权限和后台会话。

## B/S 网站交付与开发约束

最终作品以 B/S Web 网站系统形态交付，沿用当前 Django + Vue 3 前后端分离工程，不另建独立网站工程。完整业务链路为：

```text
Vue 前端上传航拍图像
  → Django 接收并保存文件
  → 离线训练权重执行推理
  → 返回语义分割 mask、灾情类别、置信度和不确定性
  → mask 转换为带优先级的复查任务点
  → 配置虚拟无人机和调度算法
  → 二维画布渲染任务、航线和状态
  → 模拟故障/低电量并触发动态重规划
  → 展示量化指标并导出 CSV 实验报告
```

网站约束如下：

1. Web 请求只执行模型推理，禁止在 HTTP 请求链路中训练模型；训练由离线脚本完成，Web 服务只加载已训练权重。
2. 保持二维仿真定位，不接入真实 GPS、真实飞控、在线通信或硬件设备。
3. 推理或仿真耗时较长时，优先采用任务 ID 加前端轮询状态；答辩版本优先保证短流程和稳定演示。
4. Django 视图只负责参数校验、权限、服务编排和持久化；推理、任务生成、调度和仿真逻辑分别下沉到 `vision/`、`task/`、`planner/` 和 `sim/`。
5. 识别结果、仿真状态和事件记录必须通过 Django ORM 持久化，刷新页面不能丢失数据。
6. 原始数据集、mask 和模型权重属于大资产，不提交到代码仓库；演示环境提前部署权重文件。

答辩现场关闭 Django 热重载，避免模型重复加载：

```powershell
cd E:\drone
.\.venv\Scripts\Activate.ps1
python manage.py runserver 127.0.0.1:8000 --noreload
```

当前访问入口为网站首页 `http://127.0.0.1:8000/`（跳转到 Vue），管理后台为 `http://127.0.0.1:8000/admin/`，Vue 开发服务为 `http://127.0.0.1:5173/`。`runserver` 仅用于开发和单用户演示；正式部署时再评估 Uvicorn/Gunicorn、Nginx 和 PostgreSQL。

## 技术栈

### 运行时与语言

| 层次 | 技术 | 用途 |
|---|---|---|
| 后端语言 | Python 3.12.5 | Django、数据处理、算法和实验脚本 |
| 前端语言 | JavaScript/HTML/CSS | Vue 页面、组件和浏览器交互 |
| 前端运行时 | Node.js 24.22.1、npm 11.19.1 | Vite 开发服务器、依赖安装和生产构建 |
| 环境隔离 | Python `.venv`、npm `package-lock.json` | 固定依赖并避免污染系统环境 |

### 后端与数据服务

| 领域 | 当前或目标技术 | 约定 |
|---|---|---|
| Web 框架 | Django 6.1.2 | URL、视图、模型、权限和管理后台 |
| 管理后台 | django-simpleui 2026.1.13 | 中文后台、业务模型管理和实验记录维护 |
| ORM | Django ORM | 业务实体、查询、事务和迁移 |
| 数据库 | SQLite（开发/演示），PostgreSQL（正式部署候选） | 第一版保持 SQLite，迁移时不要改变业务接口 |
| API | Django JSON 视图 | 以 `/api/` 为前缀，返回统一 JSON 结构；只有确有需要时再引入 DRF |
| 文件存储 | `media/` 或实验目录 | 图像、mask、权重、报告使用相对路径和元数据管理 |

### 模式识别与机器学习

| 领域 | 技术 | 用途 |
|---|---|---|
| 深度学习 | PyTorch、torchvision | U-Net、DeepLabV3-MobileNet 等模型训练和推理 |
| 图像处理 | OpenCV、Pillow | 读取、缩放、裁剪、增强和可视化 |
| 数值计算 | NumPy | mask、坐标、特征和仿真状态计算 |
| 传统机器学习 | scikit-learn | HOG/颜色/纹理特征、SVM、随机森林和评估指标 |
| 数据分析 | pandas、Matplotlib/Plotly | 实验表格、曲线、指标报告和前端图表数据 |
| 复现实验 | 固定随机种子、YAML/JSON 配置 | 记录数据版本、参数、权重和实验结果 |

### 前端与可视化

| 领域 | 技术 | 用途 |
|---|---|---|
| UI 框架 | Vue 3 Composition API | 页面、表单、任务状态和交互逻辑 |
| 构建工具 | Vite 8.3.5 | 开发热更新、代理和生产构建 |
| 状态管理 | 组件状态；规模扩大后可使用 Pinia | 任务、无人机和仿真状态共享 |
| 图表与地图 | Plotly 或轻量 SVG/Canvas | 指标曲线、二维地图、任务点和航线 |
| 样式 | CSS，必要时引入明确的组件库 | 保持页面可读、响应式和可演示 |

### 测试、质量和交付

- Django 逻辑使用 `manage.py check`、Django `TestCase` 或 pytest 验证。
- 算法模块使用小规模确定性测试，验证约束、任务分配、故障重规划和指标计算。
- 前端至少执行 `npm run build`；新增复杂交互时补充组件或端到端测试。
- 依赖版本写入 `requirements.txt` 和 `frontend/package-lock.json`，不要只依赖全局安装。
- 生产部署前再选择 Gunicorn/Uvicorn、Nginx、PostgreSQL 和静态文件服务；开发阶段不要为此增加复杂基础设施。

### 挑战杯现场演示部署

1. 现场使用预置模型权重完成推理，绝不现场训练或下载数据集、权重。
2. 提前将权重放入 `vision/weights/`，用 CPU 完整跑通一次链路；代码不得硬性依赖 GPU。
3. 控制输入图像尺寸和任务点数量，避免现场推理或重规划超时。
4. 模型首次推理可能有冷启动，前端必须显示加载状态和可读的失败提示。
5. 单用户演示可使用 Django 开发服务器并加 `--noreload`；需要局域网访问时才使用 `0.0.0.0`，同时正确配置 `ALLOWED_HOSTS`。

## 数据库与持久化

项目需要数据库。SQLite 适合个人开发、算法实验和现场演示；如果后续有多人同时访问、后台任务或正式部署，再迁移到 PostgreSQL。不要为了第一版过早引入复杂的数据库集群。

业务数据应通过 Django Model 持久化，建议至少包含以下实体：

- `Dataset`：数据集名称、来源 URL、许可证、版本、类别和本地索引位置。
- `ModelArtifact`：模型名称、算法类型、权重路径、训练配置、数据版本和评估指标。
- `Mission`：一次灾情复查任务的名称、输入图像、状态和创建时间。
- `TaskPoint`：任务坐标、灾情类别、面积、置信度、优先级、状态和所属任务。
- `UAV`：虚拟无人机编号、位置、电量、载荷能力和当前状态。
- `SimulationRun`：调度方法、随机种子、无人机配置、任务快照、开始/结束时间和汇总指标。
- `SimulationEvent`：故障、低电量、新增任务和重规划事件，以及事件发生前后的状态。
- `ExperimentResult`：基线方法、实验参数、指标、日志路径和结果文件路径。

图像、mask、模型权重、报告和 CSV 不应直接以大字段存进数据库；文件放在受控的媒体或实验目录中，数据库只记录相对路径、文件哈希、大小、来源和版本。可变的实验参数可以使用 JSON 字段，但核心查询字段应使用明确的列和外键。

新增或修改模型后必须生成迁移并执行：

```powershell
python manage.py makemigrations
python manage.py migrate
```

重要的业务模型应注册到 SimpleUI 管理后台，并为外键、状态、创建时间和实验编号建立适当索引。API 返回的任务、无人机、仿真和实验数据应来自数据库；临时计算结果可以先保存在 `SimulationRun`，再由前端读取，不要依赖单个进程的内存状态。

运行开发环境：

```powershell
# 后端
cd E:\drone
.\.venv\Scripts\Activate.ps1
python manage.py runserver 127.0.0.1:8000

# 前端，另开一个终端
cd E:\drone\frontend
npm install
npm run dev -- --host 127.0.0.1
```

## 产品范围

必须支持以下主流程：

1. 导入一张或一批无人机航拍图像。
2. 输出受淹区域、受淹道路、受淹建筑或水体的识别结果。
3. 从 mask 或识别区域提取复查任务点，并计算可解释的任务优先级。
4. 设置 3～5 架虚拟无人机的初始位置、电量和容量。
5. 使用基线方法和群体智能方法分配任务、规划二维航线。
6. 在执行中模拟无人机故障、低电量或新增任务。
7. 自动重新分配未完成任务，并展示完成时间、总航程、重点任务完成率等指标。
8. 导出任务报告和实验 CSV。

明确不在当前范围内：真实飞控、真实 GPS、三维建图、ROS、在线通信、硬件部署和端到端多智能体强化学习。除非用户明确改变范围，否则不要引入这些内容。

## 数据与模型

主数据集使用 Kaggle 的 [Aerial Imagery Dataset - FloodNet Challenge](https://www.kaggle.com/datasets/aletbm/aerial-imagery-dataset-floodnet-challenge)，并参考 [FloodNet 官方说明](https://github.com/BinaLab/FloodNet-Supervised_v1.0) 核对标注和许可。

- 先检查图像和 mask 的对应关系，不能假设 Kaggle 页面中的所有图像都有完整分割标注。
- 院赛版本优先完成二分类“受淹区域 / 背景”，或三分类“受淹道路、受淹建筑、水体”。
- 模型优先使用预训练 U-Net 或 DeepLabV3-MobileNet。
- 默认输入裁剪为 512×512，使用旋转、翻转、亮度和随机裁剪增强。
- 记录数据来源、许可证、论文引用、数据划分和预处理方式；不要把大型原始数据集或模型权重提交到仓库。
- 如果 48 小时内无法稳定取得 FloodNet 的图像和 mask，可切换到 Kaggle 的 [AIDERdata](https://www.kaggle.com/datasets/clguo1/aiderdata) 做灾情分类，调度和仿真模块保持不变。

视觉模块的输出必须包含类别、区域面积、置信度或不确定性，方便后续任务生成和实验分析。图像没有可靠地理坐标时，只能映射到明确标注的虚拟二维地图，不得声称获得了真实地理定位结果。

## 模式识别与机器学习要求

模式识别和机器学习是本项目的核心能力，所有相关实现都要形成“数据 → 特征或表示 → 模型 → 预测 → 评估 → 任务决策”的可追溯链路。

- 模式识别任务至少覆盖灾情分类或语义分割中的一种；优先完成受淹区域、道路、建筑和水体的识别。
- 在深度学习模型之外，保留一个可解释的传统机器学习基线，例如颜色/纹理特征、HOG 特征配合 SVM 或随机森林，用于说明深度模型的实际收益。
- 训练、验证和测试集必须按固定规则划分，避免同一场景或相邻图像泄漏到不同集合。
- 预处理、特征提取、数据增强、类别不平衡处理和阈值选择都要记录在配置或实验结果中。
- 固定随机种子，保存模型配置、数据版本、训练轮次、损失曲线和最佳权重；推理代码不得依赖训练时的临时变量。
- 对错误样本进行分析，至少记录漏检、误检、边界错分和低置信度区域，并说明这些结果如何影响复查任务优先级。
- 不要在普通网页请求中同步训练模型。第一版使用离线训练和已保存权重进行推理；需要在线训练时，应设计独立任务状态和可恢复的后台作业。
- 模型输出应提供类别、概率或置信度、可选的不确定性，以及能被任务模块消费的区域坐标和面积。

建议保留两条可互相验证的路线：

1. 传统模式识别基线：手工特征或预训练特征 + SVM/随机森林。
2. 机器学习主模型：U-Net 或 DeepLabV3-MobileNet 等预训练模型微调。

两条路线必须使用相同的数据划分和测试集，比较准确性、速度、资源占用和错误类型。没有实验结果时，不要声称某个模型必然优于另一个模型。

### Web 网站模型接入约定

- 深度学习推理引擎应采用进程内单例或等价的缓存机制，在服务启动后按需加载一次权重；禁止每次 API 请求都执行 `torch.load`。
- 推理函数使用 `@torch.no_grad()` 或等价方式关闭梯度计算，并明确 CPU/GPU 设备选择；无 GPU 时必须自动回退到 CPU。
- 权重默认放在 `vision/weights/`，通过 `MODEL_DIR` 环境变量定位，禁止硬编码 `E:/drone/...` 之类的本机绝对路径。
- 传统 SVM、随机森林等 `.pkl` 文件也放入 `vision/weights/`，API 可以让前端切换深度学习模型与传统基线进行对比。
- 已加载模型的名称、算法类型、权重相对路径、数据集版本、训练配置和评估指标写入 `ModelArtifact`，并可在 SimpleUI 后台查看。
- 原始图像和生成的 mask 保存到 `media/` 或受控实验目录；数据库只保存相对路径、哈希、大小和版本，不把图片二进制直接塞入业务字段。

Web 推理调用链应保持清晰：

```text
POST /api/vision/infer
  → Django 校验并保存上传文件
  → vision/infer.py 的单例推理引擎返回 mask、类别、置信度
  → 创建 Mission 并保存 mask 相对路径
  → 返回 JSON 识别结果
  → POST /api/tasks/generate
  → task 模块解析 mask，生成 TaskPoint 并计算优先级
```

## 调度与仿真

任务优先级建议从以下因素计算：

```text
priority = 灾情等级 × 区域面积 × 识别不确定性
```

至少实现并保持可比较的四种方案：

1. 平均分配任务。
2. 最近任务优先。
3. 标准离散粒子群算法（PSO）。
4. 风险加权、支持故障后动态重规划的方法。

改进算法应明确任务编码、约束修复、适应度函数和重规划触发条件。至少考虑任务优先级、无人机剩余电量、返航余量、航程和任务时限。算法必须可重复，固定随机种子后应得到稳定结果。

仿真环境只需提供二维坐标、障碍或禁飞区域（如有）、无人机状态、任务状态、执行时间和事件队列。故障重规划应只重新分配未完成任务，并保留已完成任务和当前无人机状态。

## 目录结构与模块职责

新增模块时优先遵循以下边界；可以按实际实现合并文件，但不要把所有逻辑堆在一个视图或组件中。带有“规划中”的目录可以在第一次实现对应功能时创建：

```text
E:/drone/
├── agent.md                         # 本文件：项目目标、技术栈和代理开发规则
├── manage.py                         # Django 管理入口
├── requirements.txt                  # Python 依赖及版本
├── db.sqlite3                        # 开发/演示数据库，不存放大文件
├── drone/                            # Django 项目配置
│   ├── settings.py                   # 应用、数据库、语言、静态文件和环境配置
│   ├── urls.py                       # 根路径、API 和后台路由
│   ├── asgi.py                       # ASGI 入口
│   └── wsgi.py                       # WSGI 入口
├── core/                             # Django 业务应用
│   ├── models.py                     # Dataset、Mission、TaskPoint、UAV 等模型
│   ├── admin.py                      # SimpleUI 管理后台注册
│   ├── views.py                      # 页面或轻量 API 视图
│   ├── urls.py                       # core API 路由（创建后使用）
│   ├── serializers.py                # JSON 响应组装（需要时创建）
│   ├── services/                     # 训练、推理、任务和仿真服务编排（规划中）
│   ├── migrations/                   # Django 数据库迁移
│   └── tests/                        # 模型、API 和服务测试（规划中）
├── data/                             # 数据资产（规划中）
│   ├── raw/                          # 原始下载数据，只保留说明和忽略规则
│   ├── interim/                      # 清洗、切片和中间标注
│   ├── processed/                    # 训练/验证/测试数据索引
│   └── README.md                     # 来源、许可、版本和复现说明
├── features/                         # 传统模式识别（规划中）
│   ├── extract.py                    # HOG、颜色、纹理等特征
│   ├── classifiers.py                # SVM、随机森林等基线
│   └── evaluate.py                   # 分类指标、混淆矩阵和错误分析
├── vision/                           # 深度学习视觉模块（规划中）
│   ├── datasets.py                   # Dataset、切分和增强
│   ├── models.py                     # U-Net、DeepLabV3-MobileNet 等模型
│   ├── train.py                      # 训练入口和检查点
│   ├── infer.py                      # 单张/批量推理
│   ├── metrics.py                    # IoU、Dice、F1、召回率等
│   └── weights/                      # 本地权重目录，不提交大文件
├── task/                             # 识别结果到复查任务（规划中）
│   ├── generate.py                   # mask/区域转任务点
│   ├── priority.py                   # 灾情等级、面积、不确定性评分
│   └── schemas.py                    # 任务字段和状态枚举
├── planner/                          # 多无人机调度算法（规划中）
│   ├── baseline.py                   # 平均分配、最近邻
│   ├── pso.py                        # 标准离散 PSO
│   ├── risk_aware.py                 # 风险加权动态调度
│   └── constraints.py                # 电量、返航、航程和任务时限
├── sim/                              # 二维仿真环境（规划中）
│   ├── state.py                      # UAV、任务和地图状态
│   ├── events.py                     # 故障、低电量和新增任务
│   ├── engine.py                     # 执行和重规划循环
│   └── metrics.py                    # 时间、航程、能耗和恢复率
├── experiments/                      # 实验可复现产物（规划中）
│   ├── configs/                      # YAML/JSON 实验配置
│   ├── runs/                         # 每次运行的参数、日志和指标
│   ├── reports/                      # CSV、曲线和错误样本
│   └── seeds.py                      # 随机种子统一设置
└── frontend/                         # Vue 3 + Vite 前端
    ├── package.json                  # npm scripts 和依赖
    ├── package-lock.json             # 前端依赖锁定文件
    ├── vite.config.js                # 开发服务器和 Django 代理
    ├── index.html                    # 前端入口 HTML
    ├── src/
    │   ├── main.js                   # Vue 应用入口
    │   ├── App.vue                   # 页面壳和主流程
    │   ├── api/                      # `/api` 请求客户端（规划中）
    │   ├── components/               # 任务、地图、图表等可复用组件
    │   ├── views/                    # 首页、识别、调度、实验页面
    │   ├── stores/                   # 共享状态（需要时使用 Pinia）
    │   └── styles/                   # 全局样式和主题（需要时创建）
    ├── public/                       # 不经构建处理的静态文件
    └── dist/                         # `npm run build` 生成，默认不提交
```

目录职责边界：`features/` 只处理传统特征和基线，`vision/` 只处理深度模型，`task/` 只负责识别结果到任务点，`planner/` 不读取图像文件，`sim/` 不直接依赖 Django 请求，`core/` 负责持久化和 API 编排，`frontend/` 负责展示和用户交互。这样可以单独测试算法，也可以在没有浏览器的情况下运行实验。

当前仓库已经有 `drone/`、`core/` 和 `frontend/`。新增后端接口应放在 `core` 或清晰命名的 Django 应用中；新增前端页面和组件应放在 `frontend/src`，不要恢复 Django 模板作为主业务前端。

## 前后端约定

- Vue 页面通过 `/api/...` 调用 Django，开发环境依赖 `frontend/vite.config.js` 的代理。
- API 返回 JSON，至少包含 `success`、`data` 或 `error` 字段；错误应包含稳定的错误码和可读消息。
- 任务、无人机和仿真事件使用明确的字段名、单位和状态枚举。时间统一使用 ISO 8601 或明确的秒数单位，距离和能量单位必须在接口文档中写明。
- 长耗时训练任务不要在普通 HTTP 请求中同步阻塞；第一版可以提供离线训练和已训练权重推理，调度仿真应在短请求内完成。
- 管理后台继续由 SimpleUI 提供，模型注册、实验记录和任务结果可以按需加入 Django Admin。
- 不要把密码、密钥、数据集凭据或本地绝对路径写入前端、提交记录或日志。

建议的 API 边界如下；实现时可以分阶段增加，但命名和响应结构保持稳定：

| 方法 | 路径 | 作用 |
|---|---|---|
| GET | `/api/health` | 检查服务、模型和数据库状态 |
| POST | `/api/vision/infer` | 上传图像或传入媒体 ID，返回识别区域、类别和置信度 |
| POST | `/api/tasks/generate` | 根据识别结果生成任务点和优先级 |
| POST | `/api/plans/preview` | 使用指定调度方法计算一次计划，不立即写入执行状态 |
| POST | `/api/simulations` | 创建仿真运行并保存任务、无人机和参数快照 |
| POST | `/api/simulations/{id}/events` | 触发故障、低电量或新增任务事件 |
| GET | `/api/simulations/{id}` | 读取当前仿真状态、路线和指标 |
| GET | `/api/experiments/{id}/report` | 获取实验结果或下载 CSV 报告 |

推荐的 JSON 外层结构：

```json
{
  "success": true,
  "data": {},
  "error": null,
  "request_id": "optional-id"
}
```

失败响应必须使用合适的 HTTP 状态码，并返回稳定的 `error.code`、可读的 `error.message` 和必要的字段错误信息。上传文件使用 multipart/form-data，识别和仿真结果使用 JSON；不要在 API 中返回绝对文件路径。

## 配置与环境变量

开发机可以使用默认配置，部署或共享代码时通过环境变量覆盖：

```text
DJANGO_DEBUG=true
DJANGO_SECRET_KEY=<local-secret>
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_DATABASE_URL=sqlite:///db.sqlite3
DJANGO_MEDIA_ROOT=media/
MODEL_DIR=vision/weights/
FRONTEND_ORIGIN=http://127.0.0.1:5173
```

`.env`、实际密钥、数据集令牌和本地模型权重不得提交。`settings.py` 应为缺失的开发变量提供安全默认值，但生产环境不得继续使用示例密钥、`DEBUG=True` 或开放的 `ALLOWED_HOSTS`。

## 依赖和常用命令

首次准备环境：

```powershell
cd E:\drone
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

cd frontend
npm ci
```

修改 Python 依赖后更新锁定文件：

```powershell
python -m pip freeze > requirements.txt
```

常用验证命令：

```powershell
# Django
python manage.py check
python manage.py test

# 前端
cd frontend
npm run build
```

运行训练、推理或实验脚本时，优先使用配置文件和命令行参数，例如 `python vision/train.py --config experiments/configs/floodnet_baseline.yaml`。脚本应输出运行 ID、配置摘要、数据版本和结果路径，方便从前端或后台追溯。

## 前端要求

- 使用 Vue 3 Composition API 和可复用组件。
- 主要界面应围绕“导入图像 → 查看识别 → 生成任务 → 选择调度方法 → 触发故障 → 比较指标”展开。
- 优先保证演示流程清晰、状态可见、错误可恢复；不要为了视觉效果隐藏算法输入、输出或指标。
- 调度结果至少同时展示任务点、无人机路线、任务状态和关键指标。
- 演示页应提供一个稳定的 10～30 个任务点预置场景，避免现场训练模型或临时下载数据。

前端主页面按以下顺序组织交互：

```text
导入图像 → 查看识别结果 → 生成任务点 → 设置无人机参数
→ 选择调度算法 → 运行仿真 → 模拟故障/低电量
→ 查看动态重规划 → 查看指标 → 导出 CSV 报告
```

前端必须提供加载、成功、失败和可重试状态；应内置一个预置样例图像或样例场景按钮，避免答辩现场依赖临时上传。页面需要显示当前模型名称、模型评估指标、预测置信度和仿真状态，不能只展示没有解释的动画效果。

## 实验与评价

模式识别和机器学习实验至少记录：分类任务的准确率、精确率、召回率、F1、混淆矩阵和单张推理时间；分割任务的 mIoU、Dice/F1、召回率和单张推理时间。需要比较传统基线与深度学习模型，并保存错误样本和置信度分布。调度系统至少记录重点任务完成率、总完成时间、总航程、能耗、故障后恢复率、重规划耗时和约束违约次数。

至少完成两项消融实验：

- 去掉不确定性评分。
- 去掉动态重调度。

所有调度方法必须使用相同任务、初始位置、电量、随机种子和故障事件，结果保存为可追溯的 JSON 或 CSV。不要在没有实验数据时预先承诺改进百分比。

## 开发与验证规则

每次修改后，根据改动范围运行：

```powershell
# Django 改动
python manage.py check

# 数据库模型改动
python manage.py makemigrations
python manage.py migrate

# Vue 改动
cd frontend
npm run build
```

涉及模型或算法时，补充小规模、确定性的单元测试；测试应验证任务分配、约束、故障重规划和指标计算，而不是重复实现细节。提交前确认 Django 管理后台仍可访问、根路径仍能打开 Vue、Vite 代理仍能访问 `/admin/` 和 `/api`。

优先做小而完整的垂直切片：先让一张图像能够生成任务并完成一次二维调度，再扩展更多类别、优化算法和实验报告。每项新功能都应说明输入、输出、可验证指标和演示步骤。

## 演示验收清单

- [ ] 上传航拍图并显示识别结果。
- [ ] 展示模式识别或机器学习模型的预测类别、置信度和错误提示。
- [ ] 从识别结果生成带等级的复查任务点。
- [ ] 设置 3 架以上虚拟无人机并显示各自路线。
- [ ] 可切换最近邻、标准 PSO 和改进方法。
- [ ] 点击故障事件后，未完成任务被重新分配。
- [ ] 页面显示重点任务完成率、完成时间、总航程和重规划耗时。
- [ ] 导出任务报告或实验 CSV。
- [ ] 根路径打开 Vue 前端，`/admin/` 打开中文 SimpleUI 后台。
- [ ] Web 服务启动后模型只加载一次，多次调用推理接口不会重复加载权重。
- [ ] 前端可以切换深度学习模型和传统机器学习基线模型进行对比。
- [ ] 识别结果、仿真状态和事件全部持久化，刷新页面后数据仍可读取。
- [ ] 内置预置样例图像或样例场景，可一键启动答辩演示。
- [ ] CPU 环境可以完整跑通识别、任务生成和仿真链路。

## 参考项目决策

本文件根据“推荐群体智能软件项目”任务整理。该任务确定的项目题目为“汛巡智群——基于航拍灾情识别的多无人机协同复查与动态调度软件”，并建议以 FloodNet 为主数据集、以风险加权动态 PSO 为研究重点。实际实现、数据许可和竞赛要求发生变化时，以当前项目中的可验证事实和最新官方资料为准。

