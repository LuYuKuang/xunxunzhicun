# FloodNet 模型训练与接入

训练在 Kaggle Notebook 的 GPU 环境执行，Django 只负责加载训练产物并推理。

## Kaggle 训练

1. 新建 Notebook，`Add Data` 选择 `Aerial Imagery Dataset – FloodNet Challenge`，Settings 中将 Accelerator 设为 GPU（T4 或 P100）。
2. 先确认数据目录和 mask 编码：图像与 mask 必须一一对应，mask 应是单通道类别 ID。官方 Supervised 版本是 10 类、像素值 0–9；Kaggle 镜像可能是二分类或彩色 mask，不能直接套用默认目录。
3. 安装本项目视觉依赖并运行：

```bash
pip install torch torchvision pillow numpy
python vision/train.py \
  --data-root /kaggle/input/<实际数据目录> \
  --output-dir /kaggle/working/weights \
  --epochs 30 --size 512 --batch-size 4
```

脚本要求每个 split 具有以下任一组目录名：`train-org-img` + `train-label-img`、`train/images` + `train/masks`，验证集同理。训练结束后下载 `/kaggle/working/weights/floodnet_deeplabv3.pt`。

## PyCharm 本地训练

本项目已按 Kaggle Challenge 镜像实际结构下载了 `Train/Labeled`。该镜像的 `Validation` 没有像素 mask，因此先从有标注样本中固定划分本地验证集：

```powershell
cd E:\drone
.\.venv\Scripts\Activate.ps1
python vision\prepare_floodnet.py `
  --source-root "data\raw\floodnet_kaggle\FloodNet Challenge - Track 1\Train\Labeled" `
  --output-root data\processed\floodnet `
  --val-ratio 0.2 --seed 42
```

在 PyCharm 中将解释器设置为 `E:\drone\.venv\Scripts\python.exe`，Run/Debug Configuration 的 Script path 设为 `E:\drone\vision\train.py`，Working directory 设为 `E:\drone`，Parameters 设为：

```text
--data-root data\processed\floodnet --output-dir vision\weights --epochs 30 --batch-size 4 --size 512 --num-workers 0
```

Windows 下首次运行建议使用 `--num-workers 0`，确认训练稳定后再改成 2。训练完成后，最佳 checkpoint 会保存为 `vision/weights/floodnet_deeplabv3.pt`。

Kaggle 的 Challenge 镜像只有 `Train/Labeled` 带像素 mask，`Validation` 目录没有 mask。下载后先整理并固定留出本地验证集：

```powershell
python vision/prepare_floodnet.py `
  --source-root "data/raw/floodnet_kaggle/FloodNet Challenge - Track 1/Train/Labeled" `
  --output-root "data/processed/floodnet_512" `
  --val-ratio 0.2 --seed 42 --size 512
```

PyCharm 中将项目根目录设为 `E:\drone`，解释器设为 `E:\drone\.venv\Scripts\python.exe`。整理数据的运行参数同上；训练脚本参数为：

```text
--data-root data\processed\floodnet_512 --output-dir vision\weights --epochs 30 --batch-size 4 --size 512 --num-workers 0
```

## 本地部署

```powershell
cd E:\drone
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-vision.txt
New-Item -ItemType Directory -Force vision\weights
Copy-Item <下载的权重路径> vision\weights\floodnet_deeplabv3.pt
python manage.py runserver 127.0.0.1:8000
```

接口为 `POST /api/vision/infer/`，字段名是 `image`，内容类型为 `multipart/form-data`。可选字段 `model_artifact_id` 用来切换 `ModelArtifact` 中登记的权重。接口会保存原图和 mask，创建 `Mission`，并返回类别面积占比、淹水像素占比、平均置信度、设备和耗时。


