import numpy as np
from PIL import Image, ImageDraw

from .base import GlitchGenerator
from .utils import grain, vignette, scanlines


class WeirdcoreGenerator(GlitchGenerator):
    """怪核 / Weirdcore。

    诡异不安、刻意失真低画质：暗冷底 + 一只随 t 收缩放大的诡异大眼 + 强对比 +
    重静电噪点 + 随机故障条 + 重色差。梦境里被凝视的违和感。
    """

    name = "怪核异象"
    default_filename = "weirdcore"
    default_size = (800, 600)

    def generate(self, width=None, height=None, t=None, seed=None):
        if width is None:
            width, height = self.default_size
        rng, rnd = self._rng(t, seed)
        h, w = height, width

        # 暗冷底色
        out = np.tile(np.array((30, 30, 38), dtype=np.float32), (h, w, 1))

        # 诡异大眼
        ex = w // 2 + (0 if t is None else int(15 * np.sin(t * 2 * np.pi)))
        ey = int(h * 0.5) + (0 if t is None else int(10 * np.sin(t * 3 * np.pi)))
        R = rnd.randint(80, 120)
        img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(img)
        d.ellipse([ex - R, ey - R, ex + R, ey + R], fill=(220, 220, 210))
        ir = int(R * 0.55)
        d.ellipse([ex - ir, ey - ir, ex + ir, ey + ir],
                  fill=(rnd.randint(40, 90), rnd.randint(80, 140), rnd.randint(60, 120)))
        pr = int(ir * (0.4 + 0.2 * (0.5 + 0.5 * np.sin(0.0 if t is None else t * 2 * np.pi))))
        d.ellipse([ex - pr, ey - pr, ex + pr, ey + pr], fill=(10, 10, 15))
        out = np.array(img, dtype=np.float32)

        # 强对比
        out = (out - 128) * 1.3 + 128

        # 重静电噪点
        out = grain(out, rng, 40)

        # 随机故障条
        for _ in range(rng.randint(4, 9)):
            y = rnd.randint(0, h - 1)
            hh = rnd.randint(2, 10)
            sh = rnd.randint(-40, 40)
            out[y:y + hh] = np.roll(out[y:y + hh], sh, axis=1)

        # 重色差
        c = int(8 * np.sin(0.0 if t is None else t * 2 * np.pi))
        out[:, :, 0] = np.roll(out[:, :, 0], c, axis=1)
        out[:, :, 2] = np.roll(out[:, :, 2], -c, axis=1)

        out = scanlines(out, 0.7, 2)
        out = vignette(out, 0.5)
        out = np.clip(out, 0, 255)
        return self._time_fx(out, t, width, height, scroll=5, chroma=8, scan_drift=3, pulse=20)
