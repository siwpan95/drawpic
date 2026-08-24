import random

import numpy as np

from .base import GlitchGenerator
from .utils import draw_face_on


class FaceDrawGenerator(GlitchGenerator):
    """纯画脸故障（Pure Face Drawing Glitch）。

    用 PIL ImageDraw 直接绘制一张程式化人脸（头/眉/眼/鼻/嘴），置于暗色背景之上，
    让其成为画面绝对主体；再叠加极轻量的故障点缀（偶发 RGB 小位移 / 扫描线），
    既保持「纯画脸」的清晰可辨，又归属故障艺术生成器套件。
    """

    name = "纯画脸故障"
    default_filename = "face_draw"
    default_size = (800, 800)

    def generate(self, width=800, height=800, t=None, seed=None):
        if width is None:
            width, height = self.default_size
        rng, rnd = self._rng(t, seed)
        # 暗色渐变背景，让脸成为主体
        bg = np.zeros((height, width, 3), dtype=np.float32)
        yy = np.linspace(0, 1, height)[:, None]
        bg[:, :, 2] = (yy * 45).astype(np.float32)
        bg[:, :, 0] = (yy * 22).astype(np.float32)

        # 居中、较大的脸部区域
        fw = int(width * 0.62)
        fh = int(height * 0.78)
        fx0 = (width - fw) // 2
        fy0 = int(height * 0.10)
        fx1 = fx0 + fw
        fy1 = fy0 + fh

        out = draw_face_on(bg, fx0, fy0, fx1, fy1)

        # 轻微故障点缀：偶发 RGB 小位移（随 t 脉动）+ 偶发扫描线
        if rnd.random() < 0.6:
            s = rnd.randint(2, 7) + (0 if t is None else int(4 * np.sin(t * 4 * np.pi)))
            out[:, :, 0] = np.roll(out[:, :, 0], s, axis=1)
            out[:, :, 2] = np.roll(out[:, :, 2], -s, axis=1)
        if rnd.random() < 0.4:
            out[::3] *= 0.85

        # 叠加统一时间特效
        return self._time_fx(out, t, width, height)
