import numpy as np

from .base import GlitchGenerator
from .utils import grain, vignette, scanlines


class BackroomsGenerator(GlitchGenerator):
    """后室 / Backrooms（阈限空间的经典母体）。

    暖黄壁纸 + 潮湿地毯 + 刺眼荧光灯 + 空旷单调走廊与立柱的无限空间。
    荧光灯随 t 闪烁、整体缓慢滚动、色差脉动，营造「走不出去」的限阈不安感。
    """

    name = "后室空间"
    default_filename = "backrooms"
    default_size = (960, 640)

    def generate(self, width=None, height=None, t=None, seed=None):
        if width is None:
            width, height = self.default_size
        rng, rnd = self._rng(t, seed)
        h, w = height, width
        horizon = int(h * 0.55)

        # 墙体暖黄底
        wall = np.array((200, 185, 120), dtype=np.float32)
        out = np.tile(wall, (h, w, 1)).astype(np.float32)

        # 地毯（下部）：暖黄棕 + 杂色纹理
        carpet = np.tile(np.array((190, 160, 90), dtype=np.float32), (h - horizon, w, 1))
        carpet = carpet + rng.normal(0, 12, (h - horizon, w, 3))
        out[horizon:] = carpet

        # 墙体竖向壁纸纹理（随机暗/亮竖条）
        for _ in range(rnd.randint(20, 40)):
            x = rnd.randint(0, w)
            c = rnd.randint(-15, 15)
            out[:horizon, max(0, x - 2):x + 2] += c

        # 天花板荧光灯：明亮横条 + 随 t 闪烁 + 下方光晕
        for i in range(rnd.randint(3, 6)):
            ly = rnd.randint(0, int(horizon * 0.5))
            lh = rnd.randint(6, 14)
            flick = 1.0 if t is None else (0.72 + 0.28 * np.sin(t * 2 * np.pi * 3 + i))
            out[ly:ly + lh, :] = np.clip(out[ly:ly + lh, :] + 120 * flick, 0, 255)
            glow_h = int(horizon * 0.2)
            out[ly + lh:ly + lh + glow_h, :] = np.clip(
                out[ly + lh:ly + lh + glow_h, :] * 0.55 + 45, 0, 255)

        # 远景立柱（地平线附近暗块）
        for _ in range(rnd.randint(2, 5)):
            x = rnd.randint(0, w)
            ww = rnd.randint(10, 30)
            out[horizon - int(h * 0.15):horizon, max(0, x - ww // 2):x + ww // 2] *= 0.6

        # 颗粒 + 暗角 + 扫描线
        out = grain(out, rng, 16)
        out = vignette(out, 0.45)
        out = scanlines(out, 0.85, 2)
        out = np.clip(out, 0, 255)
        return self._time_fx(out, t, width, height, scroll=4, chroma=3, scan_drift=2, pulse=14)
