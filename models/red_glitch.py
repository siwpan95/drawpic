import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .base import GlitchGenerator


class RedGlitchGenerator(GlitchGenerator):
    """算法 3：红色粒子故障 + 涂鸦（图3）。

    增强版（对应文章「绚丽偏色 / 辣眼睛」美学）：
      - 在原有红色云团基础上，对绿色/蓝色通道做压制，强化「红色主导」偏色
      - 叠加随机 RGB 通道小位移，使红云团边缘出现彩色溢色
      - 保留水平扫描线抖动与蜘蛛网涂鸦
    """

    name = "红色粒子与扫描线"
    default_filename = "red_glitch"
    default_size = (800, 600)

    def generate(self, width=800, height=600, t=None, seed=None):
        if width is None:
            width, height = self.default_size
        rng, rnd = self._rng(t, seed)
        # 1. 生成高斯噪声矩阵
        noise = rng.normal(0.1, 0.3, (height, width))
        noise = (noise - noise.min()) / (noise.max() - noise.min()) * 255
        noise = noise.astype(np.uint8)

        # 2. 转换并模糊噪声 (形成红色云团)
        img = Image.fromarray(noise, mode='L')
        img = img.filter(ImageFilter.GaussianBlur(radius=6))
        img = img.filter(ImageFilter.CONTOUR)

        # 3. 制作红黑滤镜 (只有红色通道激活)，并压制绿蓝以强化偏色
        img_data = np.array(img)
        red = np.clip(img_data * 1.8, 0, 255)
        green = np.zeros_like(red)
        blue = np.zeros_like(red)
        img_data = np.dstack((red, green, blue)).astype(np.float32)

        # 4. 红色云团边缘做 RGB 小位移溢出（「辣眼睛」彩色边），错位量随 t 脉动
        off = 5 + (0 if t is None else int(4 * np.sin(t * 4 * np.pi)))
        img_data[:, :, 2] = np.roll(img_data[:, :, 2], off, axis=1)
        img_data[:, :, 1] = np.clip(np.roll(red, -off, axis=1) * 0.25, 0, 255)

        # 5. 叠加水平故障扫描线 (奇数行变黑)
        img_data[::2, :, :] = 0
        img_data[1::2, :, :] = img_data[1::2, :, :] * 0.7

        # 6. 绘制随机蜘蛛网状涂鸦线条
        pil_img = Image.fromarray(img_data.astype(np.uint8))
        draw = ImageDraw.Draw(pil_img)
        for _ in range(25):
            x1, y1 = rnd.randint(0, width), rnd.randint(0, height)
            x2, y2 = rnd.randint(0, width), rnd.randint(0, height)
            draw.line([(x1, y1), (x2, y2)], fill=(0, 0, 0), width=rnd.randint(1, 5))

        # 7. 叠加统一时间特效
        return self._time_fx(np.array(pil_img).astype(np.float32), t, width, height)
