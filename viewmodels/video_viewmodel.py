"""视频视图模型。

职责（与 GeneratorViewModel 平行，但产出 MP4 而非 PNG）：
- 持有所需的生成器实例与输出目录（状态）
- 把每个 GlitchGenerator 的 generate(width, height, t, seed) 在时间轴上采样为帧序列，
  合成为一个可循环、平滑运动的故障艺术视频
- 支持：单生成器成片 / 全部生成器各成一片 / 全部生成器拼接成一条「展示卷轴」
- 通过 on_progress 回调向 View 推送进度
- 记录每次生成的结果（results），文件名基于日期+哈希，绝不覆盖历史
"""
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from core.naming import build_video_filename
from core.paths import OUTPUT_DIR, ensure_output_dir
from core.video_io import VideoWriter
from models import ALL_GENERATORS

# 标签文字精灵缓存：key=文本 -> RGBA uint8 数组（仅生成一次，避免逐帧 PIL 往返）
_LABEL_SPRITES = {}


def _make_label_sprite(text: str) -> np.ndarray:
    """把生成器名称渲染成一张紧凑的 RGBA 透明精灵（只做一次）。"""
    img = Image.new("RGBA", (4096, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    draw.text((8, 8), text, fill=(235, 235, 235, 255), font=font)
    bbox = img.getbbox()
    if bbox:
        return np.array(img.crop(bbox), dtype=np.uint8)
    return np.zeros((1, 1, 4), dtype=np.uint8)


class VideoViewModel:
    def __init__(self, output_dir: str = None):
        self.output_dir = ensure_output_dir(output_dir or OUTPUT_DIR)
        self.generators = [g() for g in ALL_GENERATORS]
        self.results = []  # [{name, path, ok, error, frames}, ...]
        self.on_progress = None  # 日志回调: Callable[[str], None]
        self.on_fraction = None  # 进度比例回调: Callable[[float], None]  (0..1)

    def _emit(self, message: str):
        if self.on_progress:
            self.on_progress(message)

    def _emit_fraction(self, frac: float):
        if self.on_fraction:
            try:
                self.on_fraction(min(1.0, max(0.0, frac)))
            except Exception:
                pass

    # ---- 帧采样 ----------------------------------------------------------
    def _frame_iter(self, generator, n: int, seed: int, w: int, h: int,
                    label: bool = True):
        """生成 n 帧：t 在 [0,1) 均匀推进，seed 固定以保证结构稳定、运动平滑。"""
        for i in range(n):
            t = (i / n) if n > 1 else 0.0
            data = generator.generate(w, h, t=t, seed=seed)
            frame = np.clip(data, 0, 255).astype(np.uint8)
            if label:
                frame = self._overlay_label(frame, generator.name)
            yield frame

    @staticmethod
    def _overlay_label(frame: np.ndarray, text: str) -> np.ndarray:
        """在画面左上角叠加生成器名称（淡色，便于辨识当前效果）。

        优化：文字精灵只渲染一次并缓存，逐帧用 numpy 直接 alpha 混合，
        避免每帧都做 Image.fromarray -> draw -> np.array 的 PIL 往返开销。
        """
        sprite = _LABEL_SPRITES.get(text)
        if sprite is None or sprite.shape[0] > frame.shape[0] or sprite.shape[1] > frame.shape[1]:
            sprite = _make_label_sprite(text)
            _LABEL_SPRITES[text] = sprite
        sh, sw = sprite.shape[:2]
        pad = 10
        if sh + pad <= frame.shape[0] and sw + pad <= frame.shape[1]:
            region = frame[pad:pad + sh, pad:pad + sw].astype(np.float32)
            alpha = sprite[..., 3:4].astype(np.float32) / 255.0
            blended = region * (1 - alpha) + sprite[..., :3].astype(np.float32) * alpha
            frame[pad:pad + sh, pad:pad + sw] = blended
        return frame

    # ---- 公共入口 --------------------------------------------------------
    def render_generator(self, generator, duration: float = 4.0, fps: int = 24,
                          seed: int = None, width: int = None, height: int = None,
                          label: bool = True) -> dict:
        """将单个生成器渲染为一段 MP4。返回结果字典。"""
        w, h = (width or generator.default_size[0]), (height or generator.default_size[1])
        n = max(1, int(round(duration * fps)))
        if seed is None:
            seed = random.randint(0, 1 << 30)
        self._emit(f"正在渲染视频: {generator.name} ({n} 帧 @ {fps}fps)...")
        try:
            out_name = build_video_filename(generator.default_filename)
            abs_path = self._write_frames(
                self._frame_iter(generator, n, seed, w, h, label), out_name, fps, n
            )
            result = {"name": generator.name, "path": abs_path, "ok": True,
                      "error": None, "frames": n}
        except Exception as e:
            result = {"name": generator.name, "path": None, "ok": False,
                      "error": str(e), "frames": 0}
        self.results.append(result)
        if result["ok"]:
            self._emit(f"[OK] 已生成视频: {result['path']}")
        else:
            self._emit(f"[FAIL] 生成失败: {result['name']} - {result['error']}")
        return result

    def render_all(self, duration: float = 4.0, fps: int = 24, label: bool = True):
        """每个生成器各渲染一段独立 MP4。"""
        self.results = []
        for gen in self.generators:
            self.render_generator(gen, duration=duration, fps=fps, label=label)
        return self.results

    def render_showcase(self, duration_per: float = 3.0, fps: int = 24,
                        label: bool = True, width: int = 960, height: int = 600,
                        generators: list = None) -> dict:
        """把生成器拼接成一条「展示卷轴」单个 MP4（每个效果轮播一段）。

        generators 为 None 时使用全部生成器；否则仅拼接传入的子集。
        为保证单条视频帧尺寸一致，统一渲染到 (width, height)。
        """
        gens = generators if generators else self.generators
        self._emit(f"正在合成展示卷轴 (Showcase, {len(gens)} 个效果)...")
        try:
            out_name = build_video_filename("glitch_showcase")
            abs_path = self._write_showcase(
                duration_per, fps, label, out_name, width, height, gens
            )
            result = {"name": "展示卷轴(Showcase)", "path": abs_path, "ok": True,
                      "error": None, "frames": 0}
        except Exception as e:
            result = {"name": "展示卷轴(Showcase)", "path": None, "ok": False,
                      "error": str(e), "frames": 0}
        self.results.append(result)
        if result["ok"]:
            self._emit(f"[OK] 已生成展示视频: {result['path']}")
        else:
            self._emit(f"[FAIL] 生成失败: {result['error']}")
        return result

    # ---- 内部写出 --------------------------------------------------------
    def _write_frames(self, frame_iter, out_name: str, fps: int, total: int) -> str:
        import os
        abs_path = None
        full = os.path.join(self.output_dir, out_name)
        count = 0
        with VideoWriter(full, fps=fps) as vw:
            for frame in frame_iter:
                vw.add(frame)
                abs_path = vw.path
                count += 1
                if total:
                    self._emit_fraction(count / total)
        self._emit_fraction(1.0)
        return abs_path

    def _write_showcase(self, duration_per: float, fps: int, label: bool,
                        out_name: str, width: int, height: int,
                        generators: list = None) -> str:
        import os
        gens = generators if generators else self.generators
        n = max(1, int(round(duration_per * fps)))
        total = n * max(1, len(gens))
        count = 0
        abs_path = None
        full = os.path.join(self.output_dir, out_name)
        with VideoWriter(full, fps=fps) as vw:
            for gen in gens:
                seed = random.randint(0, 1 << 30)
                for frame in self._frame_iter(gen, n, seed, width, height, label):
                    vw.add(frame)
                    count += 1
                    self._emit_fraction(count / total)
                abs_path = vw.path
        self._emit_fraction(1.0)
        return abs_path
