import numpy as np
from PIL import Image, ImageDraw

from .base import GlitchGenerator
from .utils import grain, vignette, scanlines


class LiminalSpaceGenerator(GlitchGenerator):
    """阈限空间 / Liminal Space。

    空旷的过渡场所（空商场 / 走廊 / 大厅）：透视网格地面、冷调灰蓝天空、
    地平线雾霭、怀旧低饱和调色。网格随时间向观众「流动」，像在无限空间游荡。
    """

    name = "阈限空间"
    default_filename = "liminal"
    default_size = (960, 640)

    def generate(self, width=None, height=None, t=None, seed=None):
        if width is None:
            width, height = self.default_size
        rng, rnd = self._rng(t, seed)
        h, w = height, width
        horizon = int(h * 0.5)

        # 天空 / 天花板：冷调灰蓝渐变
        yy = np.linspace(0, 1, horizon)[:, None]
        sky = yy * np.array((150, 165, 180), dtype=np.float32) + \
              (1 - yy) * np.array((120, 135, 150), dtype=np.float32)
        sky = np.repeat(sky[:, None, :], w, axis=1)

        # 地面：透视网格（用 PIL 画放射状竖线 + 汇聚横线）
        floor_img = Image.new('RGB', (w, h - horizon), (170, 160, 150))
        d = ImageDraw.Draw(floor_img)
        # 横线（近密远疏），随 t 向前流动
        for j in range(1, 16):
            f = ((j / 16.0) + (0.0 if t is None else t)) % 1.0
            yy_floor = int((h - horizon) * (f ** 2))
            d.line([(0, yy_floor), (w, yy_floor)], fill=(95, 90, 85), width=2)
        # 竖线（自灭点向外放射）
        for i in range(-12, 13):
            xb = int(w / 2 + i * (w / 12))
            d.line([(w // 2, 0), (xb, h - horizon)], fill=(95, 90, 85), width=2)
        floor = np.array(floor_img, dtype=np.float32)

        out = np.concatenate([sky, floor], axis=0)

        # 地平线雾霭（白雾）
        for d_ in range(30):
            f = 1 - d_ / 30.0
            out[horizon - 30 + d_:horizon - 30 + d_ + 1] = \
                out[horizon - 30 + d_:horizon - 30 + d_ + 1] * (1 - 0.5 * f) + 90 * (0.5 * f)

        # 怀旧低饱和暖调（去饱和 + 暖色偏移）
        gray = out.mean(axis=2, keepdims=True)
        out = np.clip(out * 0.85 + gray * 0.15 * np.array([1.05, 0.98, 0.88]), 0, 255)

        out = grain(out, rng, 14)
        out = vignette(out, 0.4)
        out = scanlines(out, 0.9, 3)
        out = np.clip(out, 0, 255)
        return self._time_fx(out, t, width, height, scroll=3, chroma=3, scan_drift=2, pulse=10)
