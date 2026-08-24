import random

import numpy as np
from PIL import Image, ImageDraw


def draw_face_on(base: np.ndarray, fx0: int, fy0: int, fx1: int, fy1: int) -> np.ndarray:
    """在 base (H, W, 3) 的指定人脸区域内绘制一个程式化人脸（头/眼/鼻/嘴）。

    风格参考百度开发者中心《Python人脸绘制》一文中的 PIL ImageDraw 画法：
    椭圆头部 + 双眼 + 三角形鼻 + 弧线嘴。用于「毁脸派」生成器——先画出可辨认的
    人脸，再施以切割故障，使「毁容」效果在视觉上成立。纯 PIL 实现，零额外依赖。

    返回带人脸的 numpy 数组（float32，0-255）。
    """
    base = base.copy()
    h, w = base.shape[:2]
    fx0 = max(0, min(int(fx0), w - 1))
    fy0 = max(0, min(int(fy0), h - 1))
    fx1 = max(fx0 + 1, min(int(fx1), w))
    fy1 = max(fy0 + 1, min(int(fy1), h))
    fw = fx1 - fx0
    fh = fy1 - fy0
    if fw < 10 or fh < 10:
        return base

    img = Image.fromarray(base.astype(np.uint8)).convert("RGB")
    draw = ImageDraw.Draw(img)

    # 头部（椭圆，略小于区域）
    pad = int(min(fw, fh) * 0.08)
    draw.ellipse(
        [fx0 + pad, fy0 + pad, fx1 - pad, fy1 - pad],
        outline=(20, 20, 20), fill=(235, 205, 180), width=3,
    )

    # 双眼：白底 + 黑瞳
    eye_y = fy0 + int(fh * 0.42)
    eye_rx = max(2, int(fw * 0.10))
    eye_ry = max(2, int(fh * 0.07))
    brow_w = max(2, int(fh * 0.02))
    for cx in (fx0 + int(fw * 0.36), fx0 + int(fw * 0.64)):
        # 眉毛
        ex0, ex1 = cx - eye_rx, cx + eye_rx
        ey = eye_y - eye_ry - max(3, int(fh * 0.04))
        draw.line([(ex0, ey), (ex1, ey)], fill=(60, 40, 30), width=brow_w)
        # 眼睛
        draw.ellipse([cx - eye_rx, eye_y - eye_ry, cx + eye_rx, eye_y + eye_ry],
                     outline=(20, 20, 20), fill=(255, 255, 255), width=2)
        pr = max(1, int(eye_rx * 0.45))
        draw.ellipse([cx - pr, eye_y - pr, cx + pr, eye_y + pr], fill=(10, 10, 10))

    # 鼻子：朝下的三角形
    nx = fx0 + int(fw * 0.5)
    ny0 = fy0 + int(fh * 0.50)
    ny1 = fy0 + int(fh * 0.64)
    draw.polygon([(nx, ny0), (nx - int(fw * 0.07), ny1), (nx + int(fw * 0.07), ny1)],
                 outline=(20, 20, 20), fill=(220, 185, 160))

    # 嘴巴：弧线（微笑）
    mw = int(fw * 0.40)
    mh = max(4, int(fh * 0.14))
    mx = fx0 + int(fw * 0.5) - mw // 2
    my = fy0 + int(fh * 0.72)
    draw.arc([mx, my, mx + mw, my + mh], 0, 180, fill=(170, 40, 50), width=3)

    return np.array(img).astype(np.float32)


def random_base(width: int, height: int, rng=None, rnd=None) -> np.ndarray:
    """生成一张彩色抽象底图 (H, W, 3) float32，取值 0-255。

    用作各类「故障」效果的源图像，便于纯算法自包含生成。

    rng / rnd 为可选确定性随机源（由 GlitchGenerator._rng 提供）。传入后，
    同一 seed 下生成的底图结构稳定，视频各帧共用同一张底图，仅后续参数随 t 演化。
    """
    if rng is None:
        rng = np.random
    if rnd is None:
        rnd = random

    yy = np.linspace(0, 1, height)
    xx = np.linspace(0, 1, width)
    X, Y = np.meshgrid(xx, yy)  # 均为 (height, width)

    r = np.sin(X * np.pi * 2 * rng.uniform(1, 3)) * 127 + 128
    g = np.sin(Y * np.pi * 2 * rng.uniform(1, 3) + 1) * 127 + 128
    b = np.sin((X + Y) * np.pi * rng.uniform(1, 3) + 2) * 127 + 128
    base = np.dstack((r, g, b))

    # 随机叠加亮条（横/纵），增加可故障的细节
    for _ in range(rnd.randint(5, 15)):
        v = rnd.randint(120, 255)
        if rnd.random() < 0.5:
            y = rnd.randint(0, height - 1)
            base[y:y + rnd.randint(1, 8), :, :] = v
        else:
            x = rnd.randint(0, width - 1)
            base[:, x:x + rnd.randint(1, 8), :] = v

    return base.astype(np.float32)


# ---- 视频 / 美学通用后处理助手 ---------------------------------------
def grain(base: np.ndarray, rng=None, amount: float = 18) -> np.ndarray:
    """叠加高斯颗粒噪点（电影 / 录像质感）。rng 为可选确定性随机源。"""
    if rng is None:
        rng = np.random
    noise = rng.normal(0, amount, base.shape)
    return np.clip(base + noise, 0, 255)


def vignette(base: np.ndarray, strength: float = 0.45) -> np.ndarray:
    """暗角：边缘压暗，中心保留，强化「窥视 / 限阈」观感。"""
    h, w = base.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w / 2.0, h / 2.0
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / max(1e-6, np.sqrt(cx ** 2 + cy ** 2))
    mask = (1.0 - strength * dist)[..., None]
    return np.clip(base * mask, 0, 255)


def scanlines(base: np.ndarray, dark: float = 0.8, step: int = 2) -> np.ndarray:
    """CRT 扫描线：每隔 step 行压暗，制造老CRT / VHS 观感。"""
    out = base.copy()
    out[::step] *= dark
    return out


def pil_blur(base: np.ndarray, radius: float = 2) -> np.ndarray:
    """用 PIL 对画面做高斯柔化（梦核常用的朦胧记忆感）。"""
    from PIL import Image, ImageFilter
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    return np.array(img.filter(ImageFilter.GaussianBlur(radius))).astype(np.float32)
