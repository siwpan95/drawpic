import numpy as np
from PIL import Image, ImageDraw

from .base import GlitchGenerator
from .utils import grain, vignette, scanlines, pil_blur


class DreamcoreGenerator(GlitchGenerator):
    """梦核 / Dreamcore。

    粉蓝超现实渐变 + 漂浮柔和形状 + 一个程式化「笑脸存在体」+ 强柔化 + 颗粒 +
    扫描线。熟悉又陌生的童年梦境感；笑脸与漂浮物随 t 轻微浮动、呼吸。
    """

    name = "梦核意境"
    default_filename = "dreamcore"
    default_size = (900, 640)

    def generate(self, width=None, height=None, t=None, seed=None):
        if width is None:
            width, height = self.default_size
        rng, rnd = self._rng(t, seed)
        h, w = height, width

        # 粉 -> 蓝 垂直渐变
        yy = np.linspace(0, 1, h)[:, None, None]
        top = np.array((255, 210, 235), dtype=np.float32)[None, None, :]
        bot = np.array((190, 225, 255), dtype=np.float32)[None, None, :]
        out = np.repeat(yy * top + (1 - yy) * bot, w, axis=1)

        # 漂浮柔和形状
        img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(img)
        for _ in range(rng.randint(6, 12)):
            r = rnd.randint(20, 80)
            cx = rnd.randint(0, w)
            cy = rnd.randint(0, h)
            col = (rnd.randint(200, 255), rnd.randint(180, 240), rnd.randint(220, 255))
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
        out = np.array(img, dtype=np.float32)

        # 程式化笑脸存在体
        fx = w // 2 + (0 if t is None else int(20 * np.sin(t * 2 * np.pi)))
        fy = int(h * 0.55) + (0 if t is None else int(10 * np.sin(t * 4 * np.pi)))
        fr = int(min(w, h) * 0.12)
        img2 = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
        d2 = ImageDraw.Draw(img2)
        d2.ellipse([fx - fr, fy - fr, fx + fr, fy + fr], outline=(60, 40, 80), width=4)
        d2.ellipse([fx - fr // 2 - 6, fy - fr // 3, fx - fr // 2 + 6, fy - fr // 3 + 12], fill=(60, 40, 80))
        d2.ellipse([fx + fr // 2 - 6, fy - fr // 3, fx + fr // 2 + 6, fy - fr // 3 + 12], fill=(60, 40, 80))
        d2.arc([fx - fr // 2, fy + fr // 6, fx + fr // 2, fy + fr // 2], 0, 180, fill=(60, 40, 80), width=4)
        out = np.array(img2, dtype=np.float32)

        # 柔化 + 颗粒 + 扫描线 + 暗角
        out = pil_blur(out, 3)
        out = grain(out, rng, 10)
        out = scanlines(out, 0.9, 3)
        out = vignette(out, 0.3)
        out = np.clip(out, 0, 255)
        return self._time_fx(out, t, width, height, scroll=3, chroma=4, scan_drift=3, pulse=12)
