import random

import numpy as np

from .base import GlitchGenerator
from .utils import random_base, draw_face_on


def _detect_face_region(width: int, height: int) -> tuple:
    """基于「人脸通常位于画面中上部、约占中部宽度」的启发式估计人脸区域。

    返回 (x0, y0, x1, y1)。纯算法、零依赖，无需外部人脸检测库。
    """
    cx0 = int(width * 0.30)
    cx1 = int(width * 0.70)
    cy0 = int(height * 0.12)
    cy1 = int(height * 0.45)
    return cx0, cy0, cx1, cy1


class SlashGlitchGenerator(GlitchGenerator):
    """线条切割毁脸派故障（Line-cut / Face-destruction Glitch）。

    对应文章归纳的「线条切割毁脸派」：先绘制一张可辨认的程式化人脸
    （参考 Python 人脸绘制范式），再刻意用纵/横线条切割画面、并对脸部做
    重点切割与错位「毁容」处理，使破坏效果在视觉上成立。
    """

    name = "线条切割毁脸派"
    default_filename = "slash_glitch"
    default_size = (900, 600)

    def generate(self, width=900, height=600, t=None, seed=None):
        if width is None:
            width, height = self.default_size
        rng, rnd = self._rng(t, seed)
        base = random_base(width, height, rng, rnd).astype(np.float32)
        out = base.copy()

        fx0, fy0, fx1, fy1 = _detect_face_region(width, height)
        # 先画出可辨认的人脸，再对其进行切割破坏
        out = draw_face_on(out, fx0, fy0, fx1, fy1)

        # 切割错位量随 t 脉动（脸被持续「撕扯」）
        def osc(mag):
            return 0 if t is None else int(mag * np.sin(t * 2 * np.pi))

        # 1) 全局随机纵/横切割线
        for _ in range(rng.randint(15, 35)):
            if rnd.random() < 0.5:
                # 纵向切割：整列错位
                x = rnd.randint(0, width - 1)
                w = rnd.randint(1, 6)
                shift = rnd.randint(-40, 41) + osc(15)
                out[:, x:x + w] = np.roll(base[:, x:x + w], shift, axis=0)
            else:
                # 横向切割：整行错位
                y = rnd.randint(0, height - 1)
                h = rnd.randint(1, 6)
                shift = rnd.randint(-40, 41) + osc(15)
                out[y:y + h] = np.roll(base[y:y + h], shift, axis=1)

        # 2) 人脸区域重点破坏：更密、更狠的切割
        face_w = fx1 - fx0
        face_h = fy1 - fy0
        for _ in range(rng.randint(20, 40)):
            if rnd.random() < 0.5:
                x = rnd.randint(fx0, max(fx0, fx1 - 2))
                w = rnd.randint(1, 5)
                shift = rnd.randint(-30, 31) + osc(12)
                out[fy0:fy1, x:x + w] = np.roll(
                    base[fy0:fy1, x:x + w], shift, axis=0
                )
            else:
                y = rnd.randint(fy0, max(fy0, fy1 - 2))
                h = rnd.randint(1, 5)
                shift = rnd.randint(-30, 31) + osc(12)
                out[y:y + h, fx0:fx1] = np.roll(
                    base[y:y + h, fx0:fx1], shift, axis=1
                )

        # 3) 在脸部区块做「撕裂位移」：随机挖一块挪到别处
        for _ in range(rng.randint(3, 7)):
            bw = rnd.randint(20, face_w // 2)
            bh = rnd.randint(15, face_h // 2)
            bx = rnd.randint(fx0, max(fx0, fx1 - bw))
            by = rnd.randint(fy0, max(fy0, fy1 - bh))
            block = out[by:by + bh, bx:bx + bw].copy()
            # 在原脸部区域涂黑（「毁容」），再把块错位贴到附近
            out[by:by + bh, bx:bx + bw] = 0
            nx = min(max(0, bx + rnd.randint(-60, 61) + osc(20)), width - bw)
            ny = min(max(0, by + rnd.randint(-30, 31) + osc(12)), height - bh)
            out[ny:ny + bh, nx:nx + bw] = block

        # 叠加统一时间特效
        return self._time_fx(out, t, width, height)
