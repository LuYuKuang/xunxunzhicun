"""FloodNet Supervised 数据集读取与图像/mask 配对。"""

from pathlib import Path
import re


IMAGE_SUFFIXES = ('.jpg', '.jpeg', '.png', '.tif', '.tiff')


def _find_dir(root: Path, split: str, kind: str):
    names = {
        'image': [f'{split}-org-img', f'{split}_org_img', f'{split}/images', f'{split}/image', f'{split}-images'],
        'mask': [f'{split}-label-img', f'{split}_label_img', f'{split}/masks', f'{split}/mask', f'{split}-masks'],
    }[kind]
    for name in names:
        path = root / name
        if path.is_dir():
            return path
    raise FileNotFoundError(f'找不到 FloodNet {split} {kind} 目录，请检查 Kaggle 数据集目录结构。')


def paired_files(root, split):
    """按 stem 配对图像和单通道 mask，避免依赖某个 Kaggle 镜像的文件名顺序。"""
    root = Path(root)
    image_dir = _find_dir(root, split, 'image')
    mask_dir = _find_dir(root, split, 'mask')
    def key(path):
        value = path.stem.lower()
        value = re.sub(r'([_-](org|image|img|label|mask|gt|lab))$', '', value)
        return value

    images = {key(p): p for p in image_dir.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES}
    masks = {key(p): p for p in mask_dir.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES}
    pairs = [(images[key], masks[key]) for key in sorted(images.keys() & masks.keys())]
    if not pairs:
        raise RuntimeError(f'{split} 没有找到同名图像和 mask 配对。')
    return pairs


class FloodNetDataset:
    """返回 (C,H,W) float 图像和 (H,W) long 类别 mask。"""

    def __init__(self, root, split='train', size=512, augment=False):
        self.pairs = paired_files(root, split)
        self.size = int(size)
        self.augment = bool(augment)

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, index):
        import torch
        from PIL import Image
        from torchvision.transforms import functional as TF
        from torchvision.transforms import InterpolationMode

        image_path, mask_path = self.pairs[index]
        image = Image.open(image_path).convert('RGB')
        mask = Image.open(mask_path).convert('L')
        image = TF.resize(image, [self.size, self.size], interpolation=InterpolationMode.BILINEAR)
        mask = TF.resize(mask, [self.size, self.size], interpolation=InterpolationMode.NEAREST)
        if self.augment:
            if torch.rand(()) > 0.5:
                image, mask = TF.hflip(image), TF.hflip(mask)
            if torch.rand(()) > 0.5:
                image, mask = TF.vflip(image), TF.vflip(mask)
        image = TF.to_tensor(image)
        image = TF.normalize(image, [0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        mask = torch.as_tensor(list(mask.getdata()), dtype=torch.long).reshape(self.size, self.size)
        return image, mask


