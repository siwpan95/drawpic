import random

import numpy as np

from .base import GlitchGenerator
from .utils import random_base


class BlockGlitchGenerator(GlitchGenerator):
    """错位图块故障（Image Block Glitch）。

    随机截取若干矩形图块并水平错位重贴，错位后的图块再叠加 RGB 分离，
    模拟视频信号块损坏的常见观感。
    """

    name = "错位图块故障"
    default_filename = "block_glitch"
    default_size = (960, 640)

    def generate(self, width=960, height=640, t=None, seed=None):
        if width is None:
            width, height = self.default_size
        rng, rnd = self._rng(t, seed)
        base = random_base(width, height, rng, rnd).astype(np.float32)
        out = base.copy()

        num_blocks = rng.randint(20, 61)
        for _ in range(num_blocks):
            bw = rnd.randint(20, width // 4)
            bh = rnd.randint(10, height // 8)
            x = rnd.randint(0, max(0, width - bw))
            y = rnd.randint(0, max(0, height - bh))
            # 水平错位范围，保证目标位置仍在图像内
            dx = rnd.randint(-x, (width - bw) - x)
            # 错位量随 t 脉动，图块持续左右抖动（须夹紧在画面内，避免越界）
            if t is not None:
                dx += int(20 * np.sin(t * 2 * np.pi + x * 0.05))
            nx = min(max(0, x + dx), width - bw)
            assert nx + bw <= width and nx >= 0

            block = base[y:y + bh, x:x + bw].copy()
            block[:, :, 0] = np.roll(block[:, :, 0], 6, axis=1)
            block[:, :, 2] = np.roll(block[:, :, 2], -6, axis=1)

            out[y:y + bh, nx:nx + bw] = block

        # 叠加统一时间特效
        return self._time_fx(out, t, width, height)
