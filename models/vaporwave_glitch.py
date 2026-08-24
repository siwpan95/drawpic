import random

import numpy as np

from .base import GlitchGenerator
from .utils import random_base


class VaporwaveGlitchGenerator(GlitchGenerator):
    """蒸汽波交叉风格故障（Vaporwave Crossover Glitch）。

    对应文章所述故障艺术与蒸汽波（vaporwave）的跨风格交叉：
    青粉渐变底色 + 扫描线 + 网格 + 轻微 RGB 分离的怀旧数字美学。
    """

    name = "蒸汽波交叉风格"
    default_filename = "vaporwave_glitch"
    default_size = (960, 640)

    def generate(self, width=960, height=640, t=None, seed=None):
        if width is None:
            width, height = self.default_size
        rng, rnd = self._rng(t, seed)
        # 1) 青→粉 垂直渐变底（蒸汽波标志配色）
        yy = np.linspace(0, 1, height)[:, None]
        r = (yy * 255).astype(np.float32)
        g = ((1 - yy) * 200 + 40).astype(np.float32)
        b = ((1 - yy) * 255).astype(np.float32)
        out = np.dstack((r, g, b)).repeat(width, axis=1)

        # 2) 透叠一层随机彩色几何底图，增加层次
        base = random_base(width, height, rng, rnd).astype(np.float32)
        out = np.clip(out * 0.75 + base * 0.25, 0, 255)

        # 3) 透视网格（地平线 + 竖线 + 横线），营造蒸汽波「空间感」
        pil = np.zeros((height, width, 3), dtype=np.float32)
        horizon = int(height * 0.62)
        # 竖线随 t 轻微左右摆动，网格「呼吸」般晃动
        sway = 0 if t is None else int(8 * np.sin(t * 2 * np.pi))
        # 竖线（上宽下窄的透视收敛）
        for i in range(-10, 11):
            x_top = int(width / 2 + i * (width / 20) * 0.15) + sway
            x_bot = int(width / 2 + i * (width / 20) * 1.0) + sway
            for tline in range(horizon, height):
                f = (tline - horizon) / (height - horizon)
                x = int(x_top * (1 - f) + x_bot * f)
                if 0 <= x < width:
                    pil[tline, max(0, x - 1):min(width, x + 1)] = (180, 120, 220)
        # 横线（越往下越疏）
        y = horizon + 4
        gap = 4
        while y < height:
            pil[y:y + 2, :] = (180, 120, 220)
            y += gap
            gap = int(gap * 1.25)
        out = np.clip(out + pil, 0, 255)

        # 4) RGB 轻微色差分离 + 扫描线（故障 + 怀旧），色差随 t 脉动
        sr = rnd.randint(4, 13) + (0 if t is None else int(5 * np.sin(t * 3 * np.pi)))
        out[:, :, 0] = np.roll(out[:, :, 0], sr, axis=1)
        out[:, :, 2] = np.roll(out[:, :, 2], -sr, axis=1)
        out[::2] *= 0.82  # 扫描线压暗

        # 叠加统一时间特效
        return self._time_fx(out, t, width, height)
