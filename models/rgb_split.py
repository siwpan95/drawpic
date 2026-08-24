import random

import numpy as np

from .base import GlitchGenerator
from .utils import random_base


class RGBSplitGenerator(GlitchGenerator):
    """RGB 颜色分离故障（RGB Split Glitch / 色差）。

    将红、绿、蓝通道按不同量水平错位，是故障艺术最典型的表达之一。
    增强版（对应文章「辣眼睛」级偏色美学）：
      - 通道错位幅度更大、更随机
      - 随机水平「撕裂带」叠加额外色差
      - 随机增益/压暗某一通道，制造更强烈的整体偏色
    """

    name = "RGB颜色分离故障"
    default_filename = "rgb_split"
    default_size = (900, 600)

    def generate(self, width=900, height=600, t=None, seed=None):
        if width is None:
            width, height = self.default_size
        rng, rnd = self._rng(t, seed)
        base = random_base(width, height, rng, rnd)
        out = base.copy()

        # 主通道错位（更大、更随机），错位量随 t 正弦脉动，色差持续拉扯
        shift_r = rng.randint(8, 46) + (0 if t is None else int(20 * np.sin(t * 2 * np.pi)))
        shift_g = rng.randint(-20, 21) + (0 if t is None else int(10 * np.sin(t * 4 * np.pi)))
        shift_b = -shift_r
        out[:, :, 0] = np.roll(base[:, :, 0], shift_r, axis=1)
        out[:, :, 1] = np.roll(base[:, :, 1], shift_g, axis=1)
        out[:, :, 2] = np.roll(base[:, :, 2], shift_b, axis=1)

        # 随机水平「撕裂带」：在若干横带内再做一次额外色差
        for _ in range(rng.randint(3, 9)):
            y = rnd.randint(0, height - 1)
            h = rnd.randint(2, 14)
            extra = rng.randint(10, 61) + (0 if t is None else int(25 * np.sin(t * 6 * np.pi)))
            out[y:y + h, :, 0] = np.roll(out[y:y + h, :, 0], extra, axis=1)
            out[y:y + h, :, 2] = np.roll(out[y:y + h, :, 2], -extra, axis=1)

        # 随机增益/压暗某一通道，制造「辣眼睛」整体偏色
        gains = [1.0, 1.0, 1.0]
        hot = rng.randint(0, 2)
        gains[hot] *= rng.uniform(1.2, 1.6)
        cold = rng.randint(0, 2)
        if cold != hot:
            gains[cold] *= rng.uniform(0.5, 0.8)
        out = out * np.array(gains, dtype=np.float32)
        out = np.clip(out, 0, 255)

        # 叠加统一时间特效
        return self._time_fx(out, t, width, height)
