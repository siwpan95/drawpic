import os

import numpy as np
from PIL import Image

from .paths import resolve_path


def save_image_from_array(data, path) -> str:
    """将 numpy 数组 (H, W, 3) 裁剪到 0-255 并保存为图片，返回绝对路径。"""
    path = resolve_path(path)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    data = np.clip(data, 0, 255).astype(np.uint8)
    img = Image.fromarray(data)
    img.save(path)
    return path
