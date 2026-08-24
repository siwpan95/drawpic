import numpy as np

from .base import GlitchGenerator
from .utils import grain, vignette, scanlines


class PoolcoreGenerator(GlitchGenerator):
    """池核 / Poolcore。

    冷清的青蓝空泳池：瓷砖网格 + 焦散光波纹 + 水面波光。平静表面下藏神秘；
    焦散相位与波光随 t 流动，像凝视一池静止却仍在呼吸的水。
    """

    name = "池核水域"
    default_filename = "poolcore"
    default_size = (960, 640)

    def generate(self, width=None, height=None, t=None, seed=None):
        if width is None:
            width, height = self.default_size
        rng, rnd = self._rng(t, seed)
        h, w = height, width

        # 青蓝垂直渐变
        yy = np.linspace(0, 1, h)[:, None, None]
        top = np.array((120, 210, 225), dtype=np.float32)[None, None, :]
        bot = np.array((40, 120, 170), dtype=np.float32)[None, None, :]
        out = np.repeat(yy * top + (1 - yy) * bot, w, axis=1)

        # 泳池瓷砖网格（勾缝线压暗）
        tile = rnd.choice([32, 48, 64])
        for y in range(0, h, tile):
            out[int(y):int(y) + 2, :] *= 0.7
        for x in range(0, w, tile):
            out[:, int(x):int(x) + 2] *= 0.7

        # 焦散光（正弦波纹），相位随 t 流动
        X, Y = np.meshgrid(np.linspace(0, 8, w), np.linspace(0, 8, h))
        ph = 0.0 if t is None else t * 2 * np.pi
        caustic = np.sin(X * 3 + ph) * np.sin(Y * 3 - ph) * 0.5 + 0.5
        out *= (0.8 + 0.4 * caustic)[:, :, None]
        # 水面波光
        out += (18 * np.sin(Y * 10 + ph) * np.cos(X * 6))[:, :, None]

        out = grain(out, rng, 8)
        out = vignette(out, 0.35)
        out = np.clip(out, 0, 255)
        return self._time_fx(out, t, width, height, scroll=4, chroma=3, scan_drift=2, pulse=10)
