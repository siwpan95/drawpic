#!/usr/bin/env python3
"""无头自检：全部故障生成器算法、PNG 图像往返、唯一文件名。

只 import models / core 中的算法层，不会创建 Tkinter 窗口。
运行：python selfcheck.py
"""
import re
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def fail(msg):
    print(f"FAIL: {msg}")
    raise SystemExit(1)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    try:
        import models
        from core import image_io, naming
    except Exception as exc:  # pragma: no cover
        fail(f"导入算法层失败: {exc}")

    from PIL import Image

    # ---------- 1. 全部生成器：输出规格 + 同 seed 可复现 + 随 t 演化 ----------
    # 部分生成器的随机区间与画布尺寸相关，160x120 是全部 21 个生成器都能工作的最小尺寸
    width, height, seed = 160, 120, 11
    for cls in models.ALL_GENERATORS:
        try:
            gen = cls()
            frame = gen.generate(width, height, seed=seed)
            again = gen.generate(width, height, seed=seed)
            frame_t = gen.generate(width, height, t=0.5, seed=seed)
        except Exception as exc:
            fail(f"{cls.__name__} 生成失败: {exc!r}")
        if frame.shape != (height, width, 3):
            fail(f"{cls.__name__} 形状不符: {frame.shape}")
        if not np.issubdtype(frame.dtype, np.number):
            fail(f"{cls.__name__} 数据类型非数值: {frame.dtype}")
        if not np.all(np.isfinite(frame)) or frame.min() < 0 or frame.max() > 255:
            fail(f"{cls.__name__} 像素越界或含 NaN")
        if frame.max() == frame.min():
            fail(f"{cls.__name__} 输出为纯色，未产生故障纹理")
        if not np.array_equal(frame, again):
            fail(f"{cls.__name__} 相同 seed 输出不一致（不可复现）")
        if np.array_equal(frame, frame_t):
            fail(f"{cls.__name__} 对 t 无响应（视频模式无动画）")

    # ---------- 2. PNG 保存 / 读回往返 ----------
    source = models.ALL_GENERATORS[0]().generate(64, 48, seed=5)
    with tempfile.TemporaryDirectory() as tmp:
        png_path = Path(tmp) / "frame.png"
        saved = image_io.save_image_from_array(source, str(png_path))
        if not Path(saved).is_file():
            fail("save_image_from_array 未生成文件")
        loaded = np.array(Image.open(saved).convert("RGB"))
    expected = np.clip(source, 0, 255).astype(np.uint8)
    if loaded.shape != expected.shape or not np.array_equal(loaded, expected):
        fail("PNG 保存后读回的数据与源数组不一致")

    # ---------- 3. 唯一文件名 ----------
    names = [naming.build_filename("glitch") for _ in range(200)]
    if len(set(names)) != len(names):
        fail("build_filename 出现重名（唯一性不足）")
    pattern = re.compile(r"^glitch_\d{8}_\d{6}_[0-9a-f]{8}\.png$")
    if not all(pattern.match(n) for n in names):
        fail("build_filename 命名格式不符")
    if not naming.build_video_filename("glitch").endswith(".mp4"):
        fail("build_video_filename 扩展名不是 .mp4")

    print(
        f"selfcheck ok: {len(models.ALL_GENERATORS)} 个故障生成器（形状/取值/同 seed 复现/随 t 动画）、"
        "PNG 图像保存读回一致、200 个唯一文件名"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
