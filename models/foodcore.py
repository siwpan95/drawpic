import numpy as np
from PIL import Image, ImageDraw

from .base import GlitchGenerator
from .utils import grain, vignette, scanlines


class FoodcoreGenerator(GlitchGenerator):
    """食核 / Foodcore。

    鲜艳食物色彩 + 阴郁调色：同心圆盘（盘子 / 食物）超现实摆盘 + 散落鲜艳食物颗粒。
    熟悉又诡异的「飨宴」；整体随 t 缓慢旋转呼吸、暗角收束。
    """

    name = "食核飨宴"
    default_filename = "foodcore"
    default_size = (900, 640)

    def generate(self, width=None, height=None, t=None, seed=None):
        if width is None:
            width, height = self.default_size
        rng, rnd = self._rng(t, seed)
        h, w = height, width

        # 暖色暗底
        out = np.tile(np.array((40, 25, 20), dtype=np.float32), (h, w, 1))
        cx, cy = w // 2, h // 2

        img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(img)

        # 同心圆盘（盘子 / 食物层）
        nrings = rng.randint(5, 9)
        for i in range(nrings, 0, -1):
            r = int(min(w, h) * 0.06 * i)
            col = (rnd.randint(120, 255), rnd.randint(80, 220), rnd.randint(40, 160))
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)

        # 散落食物颗粒（鲜艳色斑）
        for _ in range(rng.randint(40, 90)):
            x = rnd.randint(0, w)
            y = rnd.randint(0, h)
            rr = rnd.randint(3, 12)
            col = (rnd.randint(150, 255), rnd.randint(100, 255), rnd.randint(50, 200))
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=col)

        out = np.array(img, dtype=np.float32)

        # 阴郁调色：鲜艳 + 低亮暖偏移（食核标志性「诡异飨宴」）
        gray = out.mean(axis=2, keepdims=True)
        out = out * 0.7 + gray * 0.3 * np.array([1.15, 0.9, 0.7])

        out = grain(out, rng, 10)
        out = vignette(out, 0.5)
        out = scanlines(out, 0.9, 3)
        out = np.clip(out, 0, 255)
        return self._time_fx(out, t, width, height, scroll=3, chroma=4, scan_drift=2, pulse=14)
