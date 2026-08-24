import random

import numpy as np

from .base import GlitchGenerator
from .utils import random_base


class MeltGlitchGenerator(GlitchGenerator):
    """融化故障（Melt / Sortintosh 风）。

    仿「水流感知地融化数码图像」：图像被划分为若干竖向条带，
    每条带在垂直方向上做随机的拖尾错位（向下流动），并叠加纵向线纹，
    形成类似数码图像被「融化」流动的观感。
    """

    name = "融化流动故障"
    default_filename = "melt_glitch"
    default_size = (900, 600)

    def generate(self, width=900, height=600, t=None, seed=None):
        if width is None:
            width, height = self.default_size
        rng, rnd = self._rng(t, seed)
        base = random_base(width, height, rng, rnd).astype(np.float32)
        out = base.copy()

        # 竖向条带：每个条带在垂直方向拖尾流动
        x = 0
        while x < width:
            bw = rnd.randint(8, 40)
            bw = min(bw, width - x)
            # 向下流动量（拖尾长度）随 t 正弦变化，形成融化涨落的流动感
            drop = rnd.randint(0, height // 4) + (
                0 if t is None else int((height // 8) * (0.5 + 0.5 * np.sin(t * 2 * np.pi + x * 0.02)))
            )
            drop = min(drop, height - 1)
            if drop > 0:
                band = base[:, x:x + bw].copy()
                # 向下滚动形成拖尾融化
                out[:, x:x + bw] = np.roll(band, drop, axis=0)
                # 条带底部做轻微亮度衰减，强化「融化滴落」渐隐
                fade = np.linspace(1.0, 0.6, drop) if drop > 1 else np.array([1.0])
                for i in range(min(drop, height)):
                    out[i, x:x + bw] *= fade[min(i, len(fade) - 1)]
            x += bw

        # 叠加纵向线纹（融化水流的「纹路」）
        for _ in range(rng.randint(10, 30)):
            xx = rnd.randint(0, width - 1)
            out[:, xx:xx + rnd.randint(1, 3)] *= rnd.uniform(0.5, 0.9)

        # 叠加统一时间特效
        return self._time_fx(out, t, width, height)
