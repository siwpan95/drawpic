import random

import numpy as np

from .base import GlitchGenerator
from .utils import random_base


class ScanlineGlitchGenerator(GlitchGenerator):
    """扫描线抖动故障（Line / Scanline Glitch）。

    每一行按正弦波形做不同水平位移形成波浪扭曲，再叠加 CRT 扫描线压暗效果。
    """

    name = "扫描线抖动故障"
    default_filename = "scanline_glitch"
    default_size = (900, 600)

    def generate(self, width=900, height=600, t=None, seed=None):
        if width is None:
            width, height = self.default_size
        rng, rnd = self._rng(t, seed)
        base = random_base(width, height, rng, rnd).astype(np.float32)
        out = np.zeros_like(base)

        amp = rng.randint(5, 31)
        freq = rng.uniform(0.5, 3.0)
        # 相位随 t 连续推进 -> 波浪扭曲平滑流动（最直观的「动起来」）
        phase = (rng.uniform(0, 6.2832) + (0.0 if t is None else t * 2 * np.pi))
        amp_t = amp + (0 if t is None else int(8 * np.sin(t * 3 * np.pi)))

        for y in range(height):
            shift = int(amp_t * np.sin(freq * y * 0.05 + phase))
            out[y] = np.roll(base[y], shift, axis=0)

        # CRT 扫描线：偶数行压暗
        out[::2] *= 0.7
        # 叠加统一时间特效
        return self._time_fx(out, t, width, height)
