import numpy as np

from .base import GlitchGenerator


class MathGlitchGenerator(GlitchGenerator):
    """算法 1：数学函数干涉对称故障（图1）。"""

    name = "数学条纹干涉"
    default_filename = "math_glitch"
    default_size = (800, 600)

    def generate(self, width=800, height=600, t=None, seed=None):
        if width is None:
            width, height = self.default_size
        # 1. 生成二维坐标网格
        x = np.linspace(-10, 10, width)
        y = np.linspace(-10, 10, height)
        X, Y = np.meshgrid(x, y)

        # 2. 利用三角函数叠加生成干涉图案，映射到 R, G, B 通道
        #    相位随 t 连续推进，使干涉条纹平滑流动起来
        phase = 0.0 if t is None else t * 2 * np.pi
        R = (np.sin(X + phase) * np.cos(Y) + np.sin(Y * 0.5) * np.cos(X * 2 + phase))
        G = (np.cos(X * 0.7) * np.sin(Y * 1.3 - phase) - np.sin(X * 0.5))
        B = (np.sin(X * 1.2 + Y * 0.8 + phase))

        # 3. 归一化到 [0, 1] 并转为 [0, 255]
        def norm(arr):
            return (arr - arr.min()) / (arr.max() - arr.min())

        R, G, B = norm(R), norm(G), norm(B)
        img_data = np.dstack((R, G, B)) * 255

        # 4. 添加 CRT 电视扫描线 (每隔一行变暗)
        img_data[::2, :, :] *= 0.6

        # 5. 叠加统一时间特效（滚动/色差脉动/扫描线漂移）
        return self._time_fx(img_data, t, width, height)
