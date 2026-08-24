import random

import numpy as np

from .base import GlitchGenerator
from .utils import random_base


class TileJitterGenerator(GlitchGenerator):
    """图块抖动故障（Tile Jitter Glitch）。

    将图像切分为网格图块，随机微小抖动每块位置，形成数字信号抖动的碎裂感。
    """

    name = "图块抖动故障"
    default_filename = "tile_jitter"
    default_size = (960, 640)

    def generate(self, width=960, height=640, t=None, seed=None):
        if width is None:
            width, height = self.default_size
        rng, rnd = self._rng(t, seed)
        base = random_base(width, height, rng, rnd).astype(np.float32)
        out = np.zeros_like(base)

        tile = rnd.choice([32, 48, 64])
        # 抖动幅度随 t 脉动，图块像数字信号一样持续「颤动」
        amp = 8
        amp_t = amp + (0 if t is None else int(5 * (0.5 + 0.5 * np.sin(t * 2 * np.pi))))
        for ty in range(0, height, tile):
            for tx in range(0, width, tile):
                h = min(tile, height - ty)
                w = min(tile, width - tx)
                jx = rnd.randint(-min(amp_t, tx), min(amp_t, width - (tx + w)))
                jy = rnd.randint(-min(amp_t, ty), min(amp_t, height - (ty + h)))
                sx, sy = tx + jx, ty + jy
                out[sy:sy + h, sx:sx + w] = base[ty:ty + h, tx:tx + w]

        # 叠加统一时间特效
        return self._time_fx(out, t, width, height)
