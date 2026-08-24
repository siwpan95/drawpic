from abc import ABC, abstractmethod

import numpy as np


class GlitchGenerator(ABC):
    """故障生成器抽象基类（Model）。

    子类只需实现 generate()，返回形状为 (H, W, 3)、取值范围 0-255 的 numpy 数组。

    为支持「从静态图片升级为视频」，generate() 额外接受两个可选参数：
      - t (float): 帧进度，取值 [0, 1)。固定结构 + 连续参数随 t 演化，使画面平滑动起来。
      - seed (int): 视频级固定随机种子。给定后，结构（几何/底图）保持稳定，仅参数随 t 动。
                    t 与 seed 缺省时退化为原有「单次静态生成」行为，保持完全向后兼容。

    子类内部应：
      - 用 self._rng(t, seed) 取代全局 random / np.random，保证可复现与可动画；
      - 把连续型参数（相位、错位量、强度）写成 t 的函数以实现平滑运动。
    基类额外提供 _time_fx()，在生成结果之上叠加一层统一的「时间驱动动态特效」，
    即使某生成器内部未做动画，视频中也能看到滚动、色差脉动、扫描线漂移等运动。
    """

    name: str = "base"
    default_filename: str = "output.png"
    default_size: tuple = (800, 600)

    def _rng(self, t: float = None, seed: int = None):
        """返回 (rng, rnd)：
          rng  : numpy.random.RandomState，用于向量化随机
          rnd  : random.Random，用于标量 random 调用
        当 seed 给定时，以 seed 为固定随机源（结构在整段视频内保持稳定，不随 t 跳变）；
        连续型运动参数应另行写成 t 的函数。seed 为 None 时回退到全局随机，
        与原有静态生成行为完全一致。
        """
        if seed is None:
            return np.random, __import__("random")
        return np.random.RandomState(int(seed)), __import__("random").Random(int(seed))

    def _time_fx(self, frame: np.ndarray, t: float, w: int, h: int,
                 scroll: float = 6.0, chroma: float = 4.0,
                 scan_drift: float = 3.0, pulse: float = 18.0) -> np.ndarray:
        """统一时间驱动特效层（对所有生成器通用，可单独开关）。

        - scroll   : 整体垂直缓慢滚动（像素/帧），制造无尽流动感
        - chroma   : 红/蓝通道随时间正弦脉动的色差分离幅度
        - scan_drift: 扫描线（暗行）随时间向下漂移
        - pulse    : 整体亮度随时间正弦呼吸的强度
        """
        if t is None:
            return frame
        out = frame.astype(np.float32)
        n = max(1, h - 1)
        ph = t * 2 * np.pi

        # 1) 垂直滚动（无缝 wrap）
        shift = int(round(scroll * np.sin(ph * 0.5))) % n if scroll else 0
        if shift:
            out = np.roll(out, shift, axis=0)

        # 2) 色差脉动：红/蓝通道按正弦错位
        if chroma:
            c = int(round(chroma * np.sin(ph)))
            if c:
                r = out[:, :, 0]
                b = out[:, :, 2]
                out[:, :, 0] = np.roll(r, c, axis=1)
                out[:, :, 2] = np.roll(b, -c, axis=1)

        # 3) 扫描线漂移：暗行图案随 t 向下移动
        if scan_drift:
            drift = int(round(scan_drift * t)) % 2
            if drift:
                out[::2] *= 0.78

        # 4) 亮度呼吸
        if pulse:
            factor = 1.0 + (pulse / 255.0) * np.sin(ph)
            out *= factor

        return np.clip(out, 0, 255)

    @abstractmethod
    def generate(self, width: int = None, height: int = None,
                 t: float = None, seed: int = None) -> np.ndarray:
        ...
