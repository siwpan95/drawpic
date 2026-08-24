import os

import numpy as np
from PIL import Image, ImageDraw

from .base import GlitchGenerator
from .utils import grain, vignette, scanlines, pil_blur


def _load_cjk_font(size: int):
    """尝试加载系统中文字体（Windows 常见路径），失败返回 None。"""
    for p in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf",
             "C:/Windows/Fonts/simsun.ttc", "C:/Windows/Fonts/msyhbd.ttc"):
        if os.path.exists(p):
            try:
                return ImageFont_truetype(p, size)
            except Exception:
                pass
    return None


# 延迟导入，避免在无字体环境下导入失败
from PIL import ImageFont as _ImageFont
ImageFont_truetype = _ImageFont.truetype


class ChineseDreamcoreGenerator(GlitchGenerator):
    """中式梦核 / Chinese Dreamcore。

    低饱和暖调 + 千禧怀旧中国元素：窗棂格栅、红灯笼、居中汉字（福/囍）+ 老电视
    雪花屏 / 扫描线 / 柔化。集体记忆的电子乡愁；文字与灯笼随 t 轻微闪动。
    """

    name = "中式梦核"
    default_filename = "chinese_dreamcore"
    default_size = (900, 640)

    def generate(self, width=None, height=None, t=None, seed=None):
        if width is None:
            width, height = self.default_size
        rng, rnd = self._rng(t, seed)
        h, w = height, width

        # 暖红金低饱和渐变
        yy = np.linspace(0, 1, h)[:, None, None]
        top = np.array((120, 70, 60), dtype=np.float32)[None, None, :]
        bot = np.array((180, 120, 80), dtype=np.float32)[None, None, :]
        out = np.repeat(yy * top + (1 - yy) * bot, w, axis=1)

        img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(img)

        # 窗棂格栅（红木色）
        grille = (110, 40, 40)
        step = 70
        for x in range(0, w, step):
            d.line([(x, 0), (x, h)], fill=grille, width=4)
        for y in range(0, h, step):
            d.line([(0, y), (w, y)], fill=grille, width=4)

        # 红灯笼（圆 + 上下盖 + 流苏）
        lx = int(w * 0.5) + (0 if t is None else int(10 * np.sin(t * 2 * np.pi)))
        ly = int(h * 0.32)
        lr = int(min(w, h) * 0.10)
        d.ellipse([lx - lr, ly - lr, lx + lr, ly + lr], fill=(200, 40, 40), outline=(120, 20, 20))
        d.rectangle([lx - lr // 2, ly - lr - 8, lx + lr // 2, ly - lr], fill=(180, 140, 40))
        d.rectangle([lx - lr // 2, ly + lr, lx + lr // 2, ly + lr + 8], fill=(180, 140, 40))
        d.line([(lx, ly + lr + 8), (lx, ly + lr + 30)], fill=(220, 180, 60), width=3)

        # 居中汉字（福 / 囍），无字体时退化为红色方块印
        font = _load_cjk_font(int(min(w, h) * 0.22))
        char = rnd.choice(["福", "囍", "梦"])
        if font is not None:
            bbox = d.textbbox((0, 0), char, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            d.text(((w - tw) // 2 - bbox[0], (h - th) // 2 - bbox[1]), char,
                   fill=(60, 20, 20), font=font)
        else:
            s = int(min(w, h) * 0.18)
            d.rectangle([(w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2],
                        fill=(150, 30, 30))

        out = np.array(img, dtype=np.float32)

        # 老电视：柔化 + 雪花 + 扫描线 + 暗角 + 暖调
        out = pil_blur(out, 1.5)
        out = grain(out, rng, 22)
        out = scanlines(out, 0.78, 2)
        out = vignette(out, 0.5)
        gray = out.mean(axis=2, keepdims=True)
        out = np.clip(out * 0.9 + gray * 0.1 * np.array([1.1, 0.95, 0.8]), 0, 255)
        return self._time_fx(out, t, width, height, scroll=2, chroma=3, scan_drift=3, pulse=10)
