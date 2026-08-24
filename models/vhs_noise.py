import random

import numpy as np

from .base import GlitchGenerator
from .utils import random_base


class VHSNoiseGenerator(GlitchGenerator):
    """VHS 磁带噪点故障（VHS / 磁迹失真）。

    叠加高斯噪点、随机水平磁迹错位带与蓝色通道溢色，模拟老式录像带失真。
    """

    name = "VHS磁带噪点故障"
    default_filename = "vhs_noise"
    default_size = (960, 600)

    def generate(self, width=960, height=600, t=None, seed=None):
        if width is None:
            width, height = self.default_size
        rng, rnd = self._rng(t, seed)
        base = random_base(width, height, rng, rnd).astype(np.float32)

        # 高斯噪点
        noise = rng.normal(0, 22, (height, width, 1))
        out = np.clip(base + noise, 0, 255)

        # 随机水平磁迹错位带，错位量随 t 脉动（磁迹抖动）
        for _ in range(rng.randint(3, 9)):
            y = rnd.randint(0, height - 1)
            h = rnd.randint(2, 12)
            shift = rnd.randint(-35, 36) + (0 if t is None else int(18 * np.sin(t * 6 * np.pi)))
            band = out[y:y + h].copy()
            out[y:y + h] = np.clip(np.roll(band, shift, axis=1) * 1.2, 0, 255)

        # 蓝色通道轻微溢色（随 t 轻微漂移）
        out[:, :, 2] = np.roll(out[:, :, 2], 3 + (0 if t is None else int(3 * np.sin(t * 3 * np.pi))), axis=1)
        # 叠加统一时间特效
        return self._time_fx(out, t, width, height)
