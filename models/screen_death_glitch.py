import random

import numpy as np

from .base import GlitchGenerator
from .utils import random_base


class ScreenDeathGlitchGenerator(GlitchGenerator):
    """花屏死机故障（Screen Death / 老电视花屏）。

    对应文章所述老式电视机的「花屏、死机」观感：大面积彩色噪点马赛克、
    随机色块斑块与整屏剧烈偏色，模拟显像管彻底「坏掉」的瞬间。
    """

    name = "花屏死机故障"
    default_filename = "screen_death_glitch"
    default_size = (960, 600)

    def generate(self, width=960, height=600, t=None, seed=None):
        if width is None:
            width, height = self.default_size
        rng, rnd = self._rng(t, seed)
        # 1) 大块彩色马赛克噪点（花屏主体）
        cell = rnd.randint(6, 16)
        cols = (width + cell - 1) // cell
        rows = (height + cell - 1) // cell
        # 每块一个随机彩色值
        tiles = rng.randint(0, 256, size=(rows, cols, 3)).astype(np.float32)
        # 用 repeat 展开为整图尺寸
        big = np.repeat(np.repeat(tiles, cell, axis=0), cell, axis=1)
        out = big[:height, :width]

        # 2) 叠加原图的局部轮廓，保留一点「还能认出是张图」的错觉
        base = random_base(width, height, rng, rnd).astype(np.float32)
        mask = (rng.rand(height, width) < 0.15)
        out[mask] = base[mask]

        # 3) 随机色块斑块（更亮、更饱和的「信号溢出」）
        for _ in range(rng.randint(8, 20)):
            bw = rnd.randint(30, width // 3)
            bh = rnd.randint(20, height // 4)
            x = rnd.randint(0, max(0, width - bw))
            y = rnd.randint(0, max(0, height - bh))
            patch = rng.randint(0, 256, size=(bh, bw, 3)).astype(np.float32)
            out[y:y + bh, x:x + bw] = np.clip(patch * 1.3, 0, 255)

        # 4) 整屏剧烈偏色（随 t 脉动地往复错位，花屏「抽搐」）
        osc = 0 if t is None else int(20 * np.sin(t * 2 * np.pi))
        out[:, :, 0] = np.roll(out[:, :, 0], rnd.randint(10, 41) + osc, axis=1)
        out[:, :, 2] = np.roll(out[:, :, 2], -(rnd.randint(10, 41) + osc), axis=1)
        out[:, :, 1] = np.clip(out[:, :, 1] * 1.2, 0, 255)

        # 叠加统一时间特效
        return self._time_fx(out, t, width, height)
