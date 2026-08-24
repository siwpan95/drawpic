"""视频 I/O：将逐帧 numpy 数组合成为 MP4（依赖 imageio[ffmpeg]）。

- VideoWriter：上下文管理器，逐帧 append_data 后关闭即落盘。
- save_video：一次性把帧列表写成视频文件。

帧要求：形状 (H, W, 3)，取值 0-255 的 numpy 数组（uint8 或 float 均可）。
"""
import os

import numpy as np

try:
    import imageio.v2 as imageio
except Exception:  # 老版本 imageio 直接暴露 get_writer
    import imageio

from .paths import resolve_path


class VideoWriter:
    """把逐帧画面写入一个 MP4 文件。

    用法:
        with VideoWriter("out.mp4", fps=24) as vw:
            for frame in frames:
                vw.add(frame)
    """

    def __init__(self, path: str, fps: int = 24, codec: str = "libx264",
                 quality: int = 8, macro_block_size=None):
        self.path = resolve_path(path)
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self.writer = imageio.get_writer(
            self.path, fps=fps, codec=codec, quality=quality,
            macro_block_size=macro_block_size,
        )

    def add(self, frame: np.ndarray):
        self.writer.append_data(np.clip(frame, 0, 255).astype(np.uint8))

    def close(self):
        try:
            self.writer.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def save_video(frames, path: str, fps: int = 24, quality: int = 8) -> str:
    """将帧列表（可迭代的 numpy 数组）合成为 MP4，返回绝对路径。"""
    path = resolve_path(path)
    with VideoWriter(path, fps=fps, quality=quality) as vw:
        for frame in frames:
            vw.add(frame)
    return path
