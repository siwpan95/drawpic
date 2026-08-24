import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .base import GlitchGenerator


class CrystalGlitchGenerator(GlitchGenerator):
    """算法 2：破碎玻璃晶体 / 色差故障（图2）。"""

    name = "晶体破碎与色差"
    default_filename = "crystal_glitch"
    default_size = (1024, 768)

    def generate(self, width=1024, height=768, t=None, seed=None):
        if width is None:
            width, height = self.default_size
        rng, rnd = self._rng(t, seed)
        # 1. 创建深色底图
        img = Image.new('RGB', (width, height), (15, 20, 30))
        draw = ImageDraw.Draw(img)

        # 2. 模拟 Voronoi 破碎多边形 (完全基于随机坐标)
        num_polygons = 120
        for _ in range(num_polygons):
            cx = rnd.randint(0, width)
            cy = rnd.randint(0, height)
            offsets = [
                (rnd.randint(-100, -30), rnd.randint(-50, -10)),
                (rnd.randint(30, 100), rnd.randint(-60, -10)),
                (rnd.randint(40, 120), rnd.randint(20, 100)),
                (rnd.randint(-80, -20), rnd.randint(30, 90)),
            ]
            points = [(cx + ox, cy + oy) for ox, oy in offsets]
            base = rnd.randint(60, 220)
            color = (base, base, min(255, base + 40))
            draw.polygon(points, fill=color, outline=(200, 200, 200, 100))

        # 3. 应用边缘增强滤镜 (创造玻璃高反光折射感)
        img = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
        img = img.filter(ImageFilter.SMOOTH)

        # 4. 核心效果：模拟镜头色差 (Chromatic Aberration)
        #    色差错位量随 t 正弦脉动，玻璃折射持续「呼吸」
        data = np.array(img)
        blue_channel = data[:, :, 2]
        red_channel = data[:, :, 0]
        osc = 0 if t is None else int(6 * np.sin(t * 2 * np.pi))
        data[:, :, 2] = np.roll(blue_channel, shift=-(12 + osc), axis=1)
        data[:, :, 0] = np.roll(red_channel, shift=(12 + osc), axis=1)

        # 5. 叠加统一时间特效
        return self._time_fx(data, t, width, height)
