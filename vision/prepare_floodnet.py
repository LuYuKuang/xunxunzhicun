"""把 Kaggle FloodNet Challenge 的 Train/Labeled 整理成 train/val 目录。

Challenge 版本的 Validation 没有像素 mask，因此从 398 个有标注样本中固定留出验证集。
"""

from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

from PIL import Image


def _key(path: Path):
    return re.sub(r'([_-](org|image|img|label|mask|gt|lab))$', '', path.stem.lower())


def _pairs(source_root: Path):
    pairs = []
    for category in ('Flooded', 'Non-Flooded'):
        image_dir = source_root / category / 'image'
        mask_dir = source_root / category / 'mask'
        images = {_key(p): p for p in image_dir.glob('*') if p.suffix.lower() in {'.jpg', '.jpeg', '.png'}}
        masks = {_key(p): p for p in mask_dir.glob('*') if p.suffix.lower() in {'.jpg', '.jpeg', '.png'}}
        for name in sorted(images.keys() & masks.keys()):
            pairs.append({'category': category, 'image': str(images[name]), 'mask': str(masks[name])})
    if not pairs:
        raise RuntimeError(f'没有找到标注图像，请检查目录：{source_root}')
    return pairs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', required=True, help='Train/Labeled 目录')
    parser.add_argument('--output-root', default='data/processed/floodnet')
    parser.add_argument('--val-ratio', type=float, default=0.2)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--size', type=int, default=512, help='预先缩放的边长，图像双线性、mask 最近邻')
    args = parser.parse_args()

    source_root = Path(args.source_root)
    output_root = Path(args.output_root)
    pairs = _pairs(source_root)
    rng = random.Random(args.seed)
    train, val = [], []
    for category in ('Flooded', 'Non-Flooded'):
        group = [item for item in pairs if item['category'] == category]
        rng.shuffle(group)
        n_val = max(1, round(len(group) * args.val_ratio))
        val.extend(group[:n_val])
        train.extend(group[n_val:])
    rng.shuffle(train)
    rng.shuffle(val)

    for split, rows in (('train', train), ('val', val)):
        image_dir = output_root / split / 'images'
        mask_dir = output_root / split / 'masks'
        image_dir.mkdir(parents=True, exist_ok=True)
        mask_dir.mkdir(parents=True, exist_ok=True)
        for row in rows:
            stem = Path(row['image']).stem
            image = Image.open(row['image']).convert('RGB')
            mask = Image.open(row['mask']).convert('L')
            image.resize((args.size, args.size), Image.Resampling.BILINEAR).save(image_dir / f'{stem}.jpg', quality=95)
            mask.resize((args.size, args.size), Image.Resampling.NEAREST).save(mask_dir / f'{stem}.png')

    manifest = {
        'source': str(source_root),
        'seed': args.seed,
        'val_ratio': args.val_ratio,
        'size': args.size,
        'train_count': len(train),
        'val_count': len(val),
        'train': train,
        'val': val,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'prepared train={len(train)} val={len(val)} output={output_root}')


if __name__ == '__main__':
    main()


