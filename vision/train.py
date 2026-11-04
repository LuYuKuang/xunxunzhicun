"""在 Kaggle GPU 或本地 GPU 上训练 FloodNet DeepLabV3-MobileNet。

示例：
  python vision/train.py --data-root /kaggle/input/floodnet --output-dir vision/weights
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ''):
    # 支持从项目根目录直接执行 `python vision/train.py`。
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _mean_iou(logits, target, num_classes):
    import torch

    predicted = logits.argmax(dim=1)
    values = []
    for class_id in range(num_classes):
        pred = predicted == class_id
        truth = target == class_id
        union = (pred | truth).sum().item()
        if union:
            values.append((pred & truth).sum().item() / union)
    return sum(values) / max(1, len(values))


def main():
    import torch
    from torch.utils.data import DataLoader

    from vision.datasets import FloodNetDataset
    from vision.models import build_model

    parser = argparse.ArgumentParser()
    parser.add_argument('--data-root', default='data/processed/floodnet_512')
    parser.add_argument('--output-dir', default='vision/weights')
    parser.add_argument('--epochs', type=int, default=30)
    parser.add_argument('--batch-size', type=int, default=4)
    parser.add_argument('--size', type=int, default=512)
    parser.add_argument('--num-classes', type=int, default=10)
    parser.add_argument('--lr', type=float, default=3e-4)
    parser.add_argument('--num-workers', type=int, default=0)
    parser.add_argument('--no-pretrained', action='store_true')
    parser.add_argument('--resume', default='', help='从已有 checkpoint 继续训练')
    args = parser.parse_args()

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    train_set = FloodNetDataset(args.data_root, 'train', args.size, augment=True)
    val_set = FloodNetDataset(args.data_root, 'val', args.size, augment=False)
    train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True, num_workers=args.num_workers, pin_memory=device.type == 'cuda')
    val_loader = DataLoader(val_set, batch_size=args.batch_size, shuffle=False, num_workers=args.num_workers, pin_memory=device.type == 'cuda')

    best_iou = -1.0
    if args.resume:
        checkpoint = torch.load(args.resume, map_location='cpu')
        if isinstance(checkpoint, dict) and 'state_dict' in checkpoint:
            args.num_classes = int(checkpoint.get('num_classes', args.num_classes))
            args.size = int(checkpoint.get('input_size', args.size))
            state_dict = checkpoint['state_dict']
            best_iou = float(checkpoint.get('val_mIoU', -1.0))
        else:
            state_dict = checkpoint
        if isinstance(state_dict, dict) and state_dict and all(key.startswith('module.') for key in state_dict):
            state_dict = {key[7:]: value for key, value in state_dict.items()}
        model = build_model(num_classes=args.num_classes, pretrained=False)
        model.load_state_dict(state_dict)
        print(f'resuming checkpoint={args.resume} best_val_mIoU={best_iou:.4f}', flush=True)
    else:
        model = build_model(num_classes=args.num_classes, pretrained=not args.no_pretrained)
    model = model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    criterion = torch.nn.CrossEntropyLoss()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss = 0.0
        for images, masks in train_loader:
            images, masks = images.to(device), masks.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(images)['out']
            loss = criterion(logits, masks)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * images.size(0)

        model.eval()
        ious = []
        with torch.inference_mode():
            for images, masks in val_loader:
                logits = model(images.to(device))['out'].cpu()
                ious.append(_mean_iou(logits, masks, args.num_classes))
        val_iou = sum(ious) / max(1, len(ious))
        train_loss = running_loss / max(1, len(train_set))
        print(f'epoch={epoch:03d} train_loss={train_loss:.4f} val_mIoU={val_iou:.4f}', flush=True)
        if val_iou > best_iou:
            best_iou = val_iou
            torch.save({
                'state_dict': model.state_dict(),
                'num_classes': args.num_classes,
                'input_size': args.size,
                'data_version': 'FloodNet-Supervised',
                'val_mIoU': val_iou,
                'epoch': epoch,
            }, output_dir / 'floodnet_deeplabv3.pt')


if __name__ == '__main__':
    main()


