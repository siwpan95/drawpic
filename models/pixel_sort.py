import random

import numpy as np

from .base import GlitchGenerator
from .utils import random_base


class PixelSortGenerator(GlitchGenerator):
    """像素排序故障（Pixel Sorting）。

    在随机连续区间内按亮度对像素排序，是 databending / 像素排序风格的标志性效果。
    """

    name = "像素排序故障"
    default_filename = "pixel_sort"
    default_size = (900, 600)

    def generate(self, width=900, height=600, t=None, seed=None):
        if width is None:
            width, height = self.default_size
        rng, rnd = self._rng(t, seed)
        out = random_base(width, height, rng, rnd).astype(np.float32)

        num_sorts = rng.randint(15, 46)
        for _ in range(num_sorts):
            y = rnd.randint(0, height - 1)
            x0 = rnd.randint(0, max(0, width - 3))
            x1 = rnd.randint(x0 + 3, width)
            seg = out[y, x0:x1]
            brightness = seg.reshape(-1, 3).sum(axis=1)
            order = brightness.argsort()
            sorted_seg = seg[order]
            # 排序后的色带随 t 水平滑动，制造流动感
            if t is not None and (x1 - x0) > 1:
                shift = int((x1 - x0) * 0.5 * np.sin(t * 2 * np.pi + y * 0.1))
                sorted_seg = np.roll(sorted_seg, shift, axis=0)
            out[y, x0:x1] = sorted_seg

        # 叠加统一时间特效
        return self._time_fx(out, t, width, height)
