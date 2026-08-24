#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""2 小时故障风格长视频生成器 — longplay.py（增强版）

基于 drawpic 项目全部 21 个生成器，生成一部约 2 小时的三幕故障艺术长视频。

三幕结构：
  Act I  "数字衰败" (0:00-0:40) — 激进故障效果，RGB撕裂、像素排序、扫描线
  Act II "信号漂移" (0:40-1:20) — 混合风格，蒸汽波 + 柔和故障，如梦似幻
  Act III "网络崩塌" (1:20-2:00) — 网络美学 + 强故障，后室、梦核、阈限空间

相比初版增强：
  · 场景转场：分段之间使用 ffmpeg xfade 滤镜做故障风转场（pixelize / hlslice 等），
    幕间使用标题卡片 + 柔和淡入淡出，告别生硬硬切。转场失败时自动回退到无损拼接。
  · 编码质量：最终合成使用 libx264 CRF 模式，固定 GOP/关键帧间隔便于拖拽定位，
    并写入 moov atom 前置（faststart）便于网络流式播放。
  · 环境音轨：可选 --audio 用 ffmpeg anoisesrc 合成棕噪声低频氛围声（drone），
    或 --audio-file 混入自备音轨，让 2 小时长片不再静音。
  · 标题卡片：片头 + 每幕分隔卡片，故障美学排版（RGB 撕裂字 + 扫描线 + 信号条）。
  · 叠加字幕：修复原版无法渲染中文生成器名（后室/梦核…）的字体问题，
    改用系统中文字体并加半透明底栏，提升可读性。
  · 断点续传 / 预览 / dry-run 全部保留。

用法:
  python longplay.py                              # 从头生成（带转场+标题卡）
  python longplay.py --resume                     # 从断点继续
  python longplay.py --preview                    # 生成 5 分钟预览版
  python longplay.py --dry-run                    # 仅打印播放列表，不生成
  python longplay.py --width 1280 --height 720 --fps 30
  python longplay.py --no-transitions             # 关闭转场（无损快速拼接）
  python longplay.py --no-titles                  # 关闭标题卡片
  python longplay.py --audio                      # 合成环境氛围音轨
  python longplay.py --audio-file bg.mp3          # 混入自备背景音乐
  python longplay.py --crf 18 --preset slow       # 更高质量编码
  python longplay.py --cleanup                    # 成功生成后清理分段文件

输出: output/longplay_YYYYMMDD_HHMMSS.mp4 (约 2 小时)
"""

import argparse
import json
import math
import os
import random
import subprocess
import sys
import time

# Windows(GBK) 下，ffmpeg/ffprobe 的 stdout/stderr 可能含 UTF-8 字节
# （如中文路径、生成器名），用默认 locale 解码会抛 UnicodeDecodeError。
# 统一给 subprocess.run 套上 UTF-8 + 容错解码，覆盖本文件全部调用点。
_orig_subprocess_run = subprocess.run
def _subprocess_run(*args, **kwargs):
    kwargs.setdefault("encoding", "utf-8")
    kwargs.setdefault("errors", "replace")
    return _orig_subprocess_run(*args, **kwargs)
subprocess.run = _subprocess_run
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── 项目路径 ──────────────────────────────────────────────
PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR))

from core.naming import build_video_filename
from core.paths import ensure_output_dir, OUTPUT_DIR
from core.video_io import VideoWriter
from models import ALL_GENERATORS

# ── 默认配置 ──────────────────────────────────────────────
DEFAULT_WIDTH = 960
DEFAULT_HEIGHT = 540
DEFAULT_FPS = 24
DEFAULT_CRF = 20
DEFAULT_PRESET = "medium"
DEFAULT_TRANSITION_DUR = 1.5     # 转场时长（秒）
PREVIEW_MINUTES = 5
TOTAL_HOURS = 2.0

INTRO_DUR = 5.0                  # 片头卡片时长（秒）
DIVIDER_DUR = 3.0                # 幕间分隔卡片时长（秒）

SEGMENT_DIR = "longplay_segments"  # 分段文件子目录
CHECKPOINT_FILE = "longplay_checkpoint.json"

# 故障风转场（在相邻普通分段之间循环使用）。
# 注意：排除 hlslice/hrslice/vuslice/vdslice 等 slice 系列 —— 部分 ffmpeg
# 构建对其绑定支持不一致（会报 "Error binding filtergraph"）。运行时还会
# 用真实分段实测，剔除本机不可用的转场。
GLITCH_TRANSITIONS = [
    "pixelize", "dissolve", "rectcrop", "diagbl", "smoothup",
    "radial", "horzclose", "circlecrop", "distance", "zoomin",
    "squeezeh", "fadegrays", "wipetl", "slideleft", "wipeleft", "fade",
]

# 每幕主题色（RGB）：用于标题卡片氛围光与字色
ACT_ACCENT = {
    1: (255, 40, 90),     # 数字衰败 — 红
    2: (0, 200, 255),     # 信号漂移 — 青
    3: (180, 60, 255),    # 网络崩塌 — 紫
}
ACT_TITLE = {
    1: "第一幕 · 数字衰败",
    2: "第二幕 · 信号漂移",
    3: "第三幕 · 网络崩塌",
}
ACT_SUBTITLE = {
    1: "DIGITAL DECAY · 激进故障 / RGB撕裂 / 像素排序",
    2: "SIGNAL DRIFT · 蒸汽波 / 柔和故障 / 如梦似幻",
    3: "NETWORK COLLAPSE · 后室 / 梦核 / 阈限空间",
}


# ══════════════════════════════════════════════════════════
#  字体解析（修复中文生成器名无法渲染的问题）
# ══════════════════════════════════════════════════════════

def _resolve_font(size: int) -> ImageFont.ImageFont:
    """按优先级查找支持中文的字体，失败回退到默认字体。"""
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",        # 微软雅黑
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",      # 黑体
        "C:/Windows/Fonts/simsun.ttc",      # 宋体
        "C:/Windows/Fonts/mingliu.ttc",     # 细明体
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()


# ══════════════════════════════════════════════════════════
#  播放列表构建
# ══════════════════════════════════════════════════════════

def build_playlist(seed: int = 42, preview: bool = False) -> list[dict]:
    """构建三幕播放列表（不含时长）。

    返回 dict 列表，每个 dict:
      {act, idx, gen_class_name, gen_display_name, seed}
    时长由调用方根据是否含标题卡片统一分配，保证总长≈目标。
    """
    rng = random.Random(seed)

    gen_classes = list(ALL_GENERATORS)      # 21 个
    glitch_gens = gen_classes[:14]          # 前 14 个故障类
    aesthetic_gens = gen_classes[14:]       # 后 7 个网络美学类

    def gen_info(gc):
        inst = gc()
        return {
            "class_name": gc.__name__,
            "display_name": inst.name,
        }

    # ── Act I: 数字衰败 ──
    act1 = []
    for i, gc in enumerate(glitch_gens):
        act1.append({"act": 1, "idx": i, **gen_info(gc),
                     "seed": rng.randint(0, 2 ** 31 - 1)})

    # ── Act II: 信号漂移（全量打乱）──
    act2_pool = list(gen_classes)
    rng.shuffle(act2_pool)
    act2 = []
    for i, gc in enumerate(act2_pool[:14]):
        act2.append({"act": 2, "idx": i, **gen_info(gc),
                     "seed": rng.randint(0, 2 ** 31 - 1)})

    # ── Act III: 网络崩塌（网络美学为主 + 强故障穿插）──
    act3_pool = list(aesthetic_gens) + list(glitch_gens[:7])
    rng.shuffle(act3_pool)
    act3 = []
    for i, gc in enumerate(act3_pool[:14]):
        act3.append({"act": 3, "idx": i, **gen_info(gc),
                     "seed": rng.randint(0, 2 ** 31 - 1)})

    return act1 + act2 + act3            # 42 段


# ══════════════════════════════════════════════════════════
#  分段 / 标题卡片渲染
# ══════════════════════════════════════════════════════════

def _find_generator(class_name: str):
    for gc in ALL_GENERATORS:
        if gc.__name__ == class_name:
            return gc
    raise ValueError(f"未找到生成器: {class_name}")


def _make_label_sprite(text: str) -> np.ndarray:
    """预渲染带半透明底栏的中文名称精灵（RGBA）。"""
    font = _resolve_font(28)
    pad_x, pad_y = 14, 10
    tmp = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    bar_h = th + pad_y * 2
    bar_w = tw + pad_x * 2
    img = Image.new("RGBA", (bar_w, bar_h), (0, 0, 0, 0))
    dd = ImageDraw.Draw(img)
    dd.rectangle([0, 0, bar_w - 1, bar_h - 1], fill=(0, 0, 0, 150))
    tx = pad_x - bbox[0]
    ty = pad_y - bbox[1]
    # 黑色描边提升可读性
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        dd.text((tx + dx, ty + dy), text, font=font, fill=(0, 0, 0, 255))
    dd.text((tx, ty), text, font=font, fill=(235, 235, 235, 255))
    return np.array(img, dtype=np.uint8)


def _overlay_label(frame: np.ndarray, sprite: np.ndarray) -> np.ndarray:
    sh, sw = sprite.shape[:2]
    pad = 12
    if sh + pad <= frame.shape[0] and sw + pad <= frame.shape[1]:
        region = frame[pad:pad + sh, pad:pad + sw].astype(np.float32)
        alpha = sprite[..., 3:4].astype(np.float32) / 255.0
        blended = region * (1 - alpha) + sprite[..., :3].astype(np.float32) * alpha
        frame[pad:pad + sh, pad:pad + sw] = blended
    return frame


def render_segment(seg: dict, output_dir: str, fps: int,
                   width: int, height: int, label: bool = True) -> str:
    """渲染单个分段为 MP4，返回文件路径。"""
    class_name = seg["class_name"]
    display_name = seg["display_name"]
    duration = seg["duration_sec"]
    s = seg["seed"]

    gen_cls = _find_generator(class_name)
    generator = gen_cls()
    n_frames = max(1, int(round(duration * fps)))

    act = seg["act"]
    idx = seg["idx"]
    seg_name = f"act{act}_{idx:02d}_{generator.default_filename}"
    out_path = os.path.join(output_dir, f"{seg_name}.mp4")

    sprite = _make_label_sprite(display_name) if label else None

    with VideoWriter(out_path, fps=fps) as vw:
        for i in range(n_frames):
            t = (i / n_frames) if n_frames > 1 else 0.0
            frame = generator.generate(width, height, t=t, seed=s)
            frame = np.clip(frame, 0, 255).astype(np.uint8)
            if sprite is not None:
                frame = _overlay_label(frame, sprite)
            vw.add(frame)

    return out_path


def _draw_title_frame(title: str, subtitle: str, w: int, h: int,
                      t: float, accent: tuple) -> np.ndarray:
    """绘制一帧故障风标题卡片。"""
    rng = random.Random(20240711)
    img = Image.new("RGB", (w, h), (8, 8, 12))
    draw = ImageDraw.Draw(img)

    # 氛围光晕
    glow = Image.new("RGB", (w, h), (0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    cx, cy = w // 2, int(h * 0.42)
    r = int(min(w, h) * 0.55)
    gdraw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=accent)
    glow = glow.filter(ImageFilter.GaussianBlur(min(w, h) * 0.25))
    img = Image.blend(img, glow, 0.22)
    draw = ImageDraw.Draw(img)

    # 随机信号条（glitch bars）
    for _ in range(7):
        y = rng.randint(0, h - 1)
        bh = rng.randint(2, 14)
        c = rng.choice([accent, (255, 255, 255), (0, 255, 200)])
        draw.rectangle([0, y, w, y + bh], fill=c)

    # 居中标题（RGB 撕裂）
    font_big = _resolve_font(max(44, h // 9))
    font_small = _resolve_font(max(20, h // 24))
    tb = draw.textbbox((0, 0), title, font=font_big)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    tx = (w - tw) / 2 - tb[0]
    ty = cy - th / 2 - tb[1]
    for dx, dy, col in [(-4, 0, (255, 0, 80)), (4, 0, (0, 255, 220)),
                        (0, 0, (245, 245, 245))]:
        draw.text((tx + dx, ty + dy), title, font=font_big, fill=col)

    # 副标题
    sb = draw.textbbox((0, 0), subtitle, font=font_small)
    sw, sh = sb[2] - sb[0], sb[3] - sb[1]
    sx = (w - sw) / 2 - sb[0]
    sy = ty + th + h * 0.06
    draw.text((sx, sy), subtitle, font=font_small, fill=(200, 200, 210))

    # 扫描线
    arr = np.array(img, dtype=np.float32)
    arr[::3] *= 0.72
    # 随时间轻微水平抖动
    shift = int(round(6 * math.sin(t * 2 * math.pi)))
    if shift:
        arr = np.roll(arr, shift, axis=1)
    return np.clip(arr, 0, 255).astype(np.uint8)


def render_title_card(title: str, subtitle: str, out_path: str, fps: int,
                      width: int, height: int, duration_sec: float,
                      accent: tuple) -> str:
    """渲染标题卡片为 MP4，返回文件路径。"""
    n_frames = max(1, int(round(duration_sec * fps)))
    with VideoWriter(out_path, fps=fps) as vw:
        for i in range(n_frames):
            t = i / n_frames
            frame = _draw_title_frame(title, subtitle, width, height, t, accent)
            vw.add(frame)
    return out_path


# ══════════════════════════════════════════════════════════
#  Clip 列表构建（含标题卡片）
# ══════════════════════════════════════════════════════════

def build_clips(playlist: list, args, segment_dir: str,
                title_total: float) -> list[dict]:
    """构建有序 clip 列表，普通分段之间按需插入片头与幕间标题卡。

    每个 clip: {kind, name, duration_sec, out_path, render}
      kind: 'segment' | 'title'
      render: 无参 callable，返回输出路径
    """
    total_seconds = (PREVIEW_MINUTES * 60) if args.preview else int(TOTAL_HOURS * 3600)
    duration_per = (total_seconds - title_total) / len(playlist)

    clips = []
    prev_act = None
    for seg in playlist:
        seg = dict(seg)
        seg["duration_sec"] = round(duration_per, 2)
        if not args.no_titles and prev_act is not None and seg["act"] != prev_act:
            accent = ACT_ACCENT[seg["act"]]
            dv = seg["act"]
            dpath = os.path.join(
                segment_dir, f"title_act{dv}_{ACT_TITLE[dv].split('·')[-1].strip()}.mp4")
            clips.append({
                "kind": "title",
                "name": ACT_TITLE[dv],
                "duration_sec": DIVIDER_DUR,
                "out_path": dpath,
                "render": (lambda p=dpath, a=accent, v=dv: render_title_card(
                    ACT_TITLE[v], ACT_SUBTITLE[v], p, args.fps,
                    args.width, args.height, DIVIDER_DUR, a)),
            })
        clips.append({
            "kind": "segment",
            "name": f"Act{seg['act']}#{seg['idx']:02d} {seg['display_name']}",
            "seg": seg,
            "duration_sec": seg["duration_sec"],
            "out_path": None,  # 由 render 内部确定，下面回填
            "render": None,
        })
        prev_act = seg["act"]

    # 回填分段输出路径与 render 闭包
    for c in clips:
        if c["kind"] == "segment":
            seg = c["seg"]
            gen_cls = _find_generator(seg["class_name"])()
            seg_name = f"act{seg['act']}_{seg['idx']:02d}_{gen_cls.default_filename}"
            c["out_path"] = os.path.join(segment_dir, f"{seg_name}.mp4")
            c["render"] = (lambda cc=c: render_segment(
                cc["seg"], segment_dir, args.fps,
                args.width, args.height, not args.no_label))

    # 片头卡片插在最前
    if not args.no_titles:
        ipath = os.path.join(segment_dir, "title_intro.mp4")
        intro = {
            "kind": "title",
            "name": "片头 · 故障长卷",
            "duration_sec": INTRO_DUR,
            "out_path": ipath,
            "render": (lambda p=ipath: render_title_card(
                "故障长卷", "GLITCH LONGPLAY · 数字衰败 / 信号漂移 / 网络崩塌",
                p, args.fps, args.width, args.height, INTRO_DUR, (120, 160, 255))),
        }
        clips.insert(0, intro)

    return clips


# ══════════════════════════════════════════════════════════
#  Checkpoint 断点续传
# ══════════════════════════════════════════════════════════

def load_checkpoint(checkpoint_path: str) -> dict:
    if os.path.exists(checkpoint_path):
        with open(checkpoint_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed_indices": [], "segment_files": []}


def save_checkpoint(checkpoint_path: str, completed_indices: list,
                    segment_files: list):
    data = {
        "completed_indices": completed_indices,
        "segment_files": segment_files,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════
#  ffmpeg 工具
# ══════════════════════════════════════════════════════════

def _require_ffmpeg():
    for tool in ("ffmpeg", "ffprobe"):
        if subprocess.run([tool, "-version"], capture_output=True,
                          text=True).returncode != 0:
            raise RuntimeError(
                f"未找到 {tool}，请先安装 FFmpeg 并加入 PATH。")


def _probe_duration(path: str) -> float | None:
    """用 ffprobe 获取视频时长（秒），失败返回 None。"""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error",
             "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True)
        if out.returncode == 0:
            return float(out.stdout.strip())
    except Exception:
        pass
    return None


def concat_with_ffmpeg(segment_files: list[str], output_path: str) -> str:
    """使用 ffmpeg concat demuxer 拼接所有分段（无损 copy），失败回退重新编码。"""
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        for seg_path in segment_files:
            abs_path = os.path.abspath(seg_path).replace("\\", "/")
            f.write(f"file '{abs_path}'\n")
        list_file = f.name

    try:
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
               "-i", list_file, "-c", "copy", output_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  [warn] concat copy 失败，回退到重新编码: "
                  f"{result.stderr[-200:]}")
            cmd2 = ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", list_file, "-c:v", "libx264", "-preset", "medium",
                    "-crf", str(DEFAULT_CRF), "-pix_fmt", "yuv420p",
                    output_path]
            result2 = subprocess.run(cmd2, capture_output=True, text=True)
            if result2.returncode != 0:
                raise RuntimeError(f"ffmpeg 拼接失败:\n{result2.stderr}")
    finally:
        os.unlink(list_file)

    return output_path


def _validate_transitions(sample_paths: list[str], candidates: list[str],
                           transition_dur: float) -> list[str]:
    """用两份真实分段探测哪些 xfade 转场在本机 ffmpeg 上可用。

    不同 ffmpeg 构建对部分转场（如 hlslice 等 slice 系列）支持不一致，
    运行前实测可避免整条滤镜图绑定失败。返回可用转场名列表。
    """
    if len(sample_paths) < 2:
        return ["fade"]
    import tempfile
    d = os.path.dirname(sample_paths[0])
    valid = []
    for tr in candidates:
        out = os.path.join(d, f".probe_{tr}.mp4")
        cmd = ["ffmpeg", "-y", "-loglevel", "error",
               "-ss", "0", "-t", "2", "-i", sample_paths[0],
               "-ss", "0", "-t", "2", "-i", sample_paths[1],
               "-filter_complex",
               f"[0:v][1:v]xfade=transition={tr}:duration=0.5:offset=1.0[vx]",
               "-map", "[vx]", "-c:v", "libx264", "-pix_fmt", "yuv420p", out]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0:
            valid.append(tr)
        if os.path.exists(out):
            os.remove(out)
    return valid or ["fade"]


def _run_xfade(clips: list[dict], output_path: str, args,
               transition_set: list[str], T: float) -> str:
    """构建并执行链式 xfade 合成（单色转场集合）。失败抛 RuntimeError。"""
    paths = [c["out_path"] for c in clips]
    durations = [_probe_duration(p) for p in paths]
    if any(d is None for d in durations):
        raise RuntimeError("无法获取分段时长，回退到无损拼接")

    n = len(paths)
    gop = max(2, int(round(args.fps * 2)))   # 约 2 秒一个关键帧，便于拖拽

    fc_parts = []
    prev = "0:v"
    cum = durations[0]
    gi = 0
    for i in range(1, n):
        offset = cum - T
        if offset < 0:
            raise RuntimeError("分段过短，无法容纳转场，回退拼接")
        # 标题卡与普通分段之间用柔和淡入，否则循环使用故障风转场
        if clips[i - 1]["kind"] == "title" or clips[i]["kind"] == "title":
            trans = "fade"
        else:
            trans = transition_set[gi % len(transition_set)]
            gi += 1
        out = f"v{i}"
        fc_parts.append(
            f"[{prev}][{i}:v]xfade=transition={trans}:duration={T}"
            f":offset={offset:.3f}[{out}]")
        cum = cum + durations[i] - T
        prev = out

    fc = ";".join(fc_parts)   # 末端不再追加 format 滤镜，改用输出 -pix_fmt

    cmd = ["ffmpeg", "-y"]
    for p in paths:
        cmd += ["-i", p]
    cmd += ["-filter_complex", fc,
            "-map", f"[{prev}]",
            "-c:v", "libx264",
            "-crf", str(args.crf),
            "-preset", args.preset,
            "-pix_fmt", "yuv420p",
            "-g", str(gop),
            "-movflags", "+faststart",
            output_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"xfade 合成失败:\n{result.stderr[-400:]}")
    return output_path


def build_video_with_transitions(clips: list[dict], output_path: str,
                                 args) -> str:
    """用 xfade 链把所有 clip 串成带转场的视频。

    先实测本机 ffmpeg 支持的转场集合，再构建滤镜图；若失败则回退到
    全 fade 转场；仍失败则由调用方回退到 concat 无损拼接。
    """
    T = args.transition_dur
    valid = _validate_transitions([c["out_path"] for c in clips],
                                  GLITCH_TRANSITIONS, T)
    # 第一遍：故障风转场集合
    try:
        return _run_xfade(clips, output_path, args, valid, T)
    except RuntimeError as e1:
        # 第二遍：保险起见全部用 fade
        try:
            return _run_xfade(clips, output_path, args, ["fade"], T)
        except RuntimeError as e2:
            raise RuntimeError(f"{e1}\n{e2}")


def mux_audio(temp_video: str, final_path: str, args,
              total_dur: float) -> str:
    """把环境音轨（合成或自备）混入视频；无音频则仅加 faststart 复制。"""
    if args.audio_file:
        cmd = ["ffmpeg", "-y", "-i", temp_video, "-i", args.audio_file,
               "-filter_complex", "[1:a]volume=0.9[aout]",
               "-map", "0:v", "-map", "[aout]",
               "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
               "-shortest", "-movflags", "+faststart", final_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"混入音轨失败:\n{result.stderr[-400:]}")
        return final_path

    if args.audio:
        dur = _probe_duration(temp_video) or total_dur
        cmd = ["ffmpeg", "-y", "-i", temp_video,
               "-f", "lavfi", "-i",
               f"anoisesrc=c=2:r=48000:d={dur:.1f}",
               "-filter_complex",
               "[1:a]lowpass=f=350,volume=0.10,"
               f"afade=t=in:st=0:d=3,afade=t=out:st={max(0,dur-3):.1f}:d=3[aout]",
               "-map", "0:v", "-map", "[aout]",
               "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
               "-shortest", "-movflags", "+faststart", final_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  [warn] 环境音合成失败，输出无声版本: {result.stderr[-200:]}")
            # 回退：仅复制视频
            subprocess.run(["ffmpeg", "-y", "-i", temp_video, "-c", "copy",
                            "-movflags", "+faststart", final_path],
                           capture_output=True, text=True)
        return final_path

    # 无音频：复制并加 faststart
    result = subprocess.run(["ffmpeg", "-y", "-i", temp_video, "-c", "copy",
                             "-movflags", "+faststart", final_path],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"最终封装失败:\n{result.stderr[-400:]}")
    return final_path


# ══════════════════════════════════════════════════════════
#  主流程
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="2 小时故障风格长视频生成器（增强版）"
    )
    parser.add_argument("--resume", action="store_true", help="从断点继续")
    parser.add_argument("--preview", action="store_true", help="生成 5 分钟预览版")
    parser.add_argument("--dry-run", action="store_true", help="仅打印播放列表")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS)
    parser.add_argument("--out", default=None, help="输出目录")
    parser.add_argument("--no-label", action="store_true", help="关闭名称叠加")
    parser.add_argument("--seed", type=int, default=42, help="播放列表随机种子")
    # 增强项
    parser.add_argument("--no-transitions", action="store_true",
                        help="关闭场景转场（无损快速拼接）")
    parser.add_argument("--no-titles", action="store_true",
                        help="关闭片头/幕间标题卡片")
    parser.add_argument("--transition-dur", type=float,
                        default=DEFAULT_TRANSITION_DUR, help="转场时长(秒)")
    parser.add_argument("--audio", action="store_true",
                        help="合成环境氛围音轨（棕噪声 drone）")
    parser.add_argument("--audio-file", default=None,
                        help="混入自备背景音轨文件路径")
    parser.add_argument("--crf", type=int, default=DEFAULT_CRF,
                        help="x264 CRF 质量(0-51, 越小越好)")
    parser.add_argument("--preset", default=DEFAULT_PRESET,
                        help="x264 编码预设(ultrafast..veryslow)")
    parser.add_argument("--cleanup", action="store_true",
                        help="成功生成后清理分段文件")
    args = parser.parse_args()

    _require_ffmpeg()

    # ── 输出目录 ──
    output_dir = ensure_output_dir(args.out or OUTPUT_DIR)
    segment_dir = os.path.join(output_dir, SEGMENT_DIR)
    os.makedirs(segment_dir, exist_ok=True)
    checkpoint_path = os.path.join(output_dir, CHECKPOINT_FILE)

    # ── 构建播放列表 / clip 列表 ──
    playlist = build_playlist(seed=args.seed, preview=args.preview)
    title_total = 0.0
    if not args.no_titles:
        title_total = INTRO_DUR + DIVIDER_DUR * 2
    clips = build_clips(playlist, args, segment_dir, title_total)

    if args.dry_run:
        print("=" * 72)
        print(f"播放列表 ({len(playlist)} 段 + {len(clips)-len(playlist)} 卡片, "
              f"预览={args.preview})")
        print("=" * 72)
        total_dur = 0
        for c in clips:
            dur = c["duration_sec"]
            total_dur += dur
            mins = int(dur // 60)
            secs = int(dur % 60)
            tag = "*" if c["kind"] == "title" else " "
            print(f"  {tag} {c['name']:<28s}  {mins}:{secs:02d}")
        total_mins = int(total_dur // 60)
        total_secs = int(total_dur % 60)
        print(f"\n预计总时长: {total_mins}:{total_secs:02d} ({total_dur:.0f}s)")
        print(f"分辨率: {args.width}×{args.height} @ {args.fps}fps")
        print(f"转场: {'关' if args.no_transitions else '开'}  "
              f"标题卡: {'关' if args.no_titles else '开'}  "
              f"音轨: {'环境' if args.audio else ('自备' if args.audio_file else '无')}")
        return

    # ── 加载断点 ──
    checkpoint = (load_checkpoint(checkpoint_path) if args.resume
                  else {"completed_indices": [], "segment_files": []})
    completed = set(checkpoint["completed_indices"])
    segment_files = list(checkpoint["segment_files"])

    print("=" * 72)
    mode = "预览" if args.preview else "正式"
    print(f"2 小时故障长视频生成器（增强版）— {mode}模式")
    print(f"分辨率: {args.width}×{args.height} @ {args.fps}fps")
    print(f"总 clip: {len(clips)} (分段 {len(playlist)} + 卡片 {len(clips)-len(playlist)})")
    print(f"转场: {'关' if args.no_transitions else '开'}  "
          f"标题卡: {'关' if args.no_titles else '开'}  "
          f"音轨: {'环境' if args.audio else ('自备' if args.audio_file else '无')}")
    if completed:
        print(f"已完成: {len(completed)}/{len(clips)} (断点续传)")
    print(f"分段输出: {segment_dir}")
    print("=" * 72)

    # ── 逐 clip 渲染 ──
    label = not args.no_label
    start_time = time.time()

    for i, c in enumerate(clips):
        out_path = c["out_path"]
        if i in completed and os.path.exists(out_path):
            print(f"  [{i + 1}/{len(clips)}] {c['name']} — 跳过 (已完成)")
            if out_path not in segment_files:
                segment_files.append(out_path)
            continue

        t0 = time.time()
        dur = c["duration_sec"]
        mins = int(dur // 60)
        secs = int(dur % 60)
        print(f"  [{i + 1}/{len(clips)}] {c['name']} "
              f"({mins}:{secs:02d})...", end=" ", flush=True)

        try:
            seg_path = c["render"]()
            elapsed = time.time() - t0
            size_mb = os.path.getsize(seg_path) / (1024 * 1024)
            print(f"OK ({elapsed:.1f}s, {size_mb:.1f}MB)")
            segment_files.append(seg_path)
        except Exception as e:
            print(f"FAIL: {e}")
            save_checkpoint(checkpoint_path, list(completed), segment_files)
            print(f"\n断点已保存到 {checkpoint_path}，可用 --resume 继续")
            sys.exit(1)

        completed.add(i)
        if (i + 1) % 5 == 0:
            save_checkpoint(checkpoint_path, list(completed), segment_files)
            elapsed_total = time.time() - start_time
            eta = (elapsed_total / (i + 1)) * (len(clips) - i - 1)
            eta_min = int(eta // 60)
            eta_sec = int(eta % 60)
            print(f"  [checkpoint] 进度 {i + 1}/{len(clips)}, "
                  f"预计剩余 {eta_min}:{eta_sec:02d}")

    total_render_time = time.time() - start_time
    render_mins = int(total_render_time // 60)
    render_secs = int(total_render_time % 60)
    print(f"\n分段渲染完成！耗时 {render_mins}:{render_secs:02d}")
    print(f"共生成 {len(segment_files)} 个 clip")

    # ── 合成最终视频 ──
    final_name = "longplay_preview" if args.preview else "longplay"
    final_name = build_video_filename(final_name)
    final_path = os.path.join(output_dir, final_name)

    # 临时视频（仅画面，用于转场/拼接）
    temp_path = os.path.join(segment_dir, "_longplay_video_only.mp4")

    print(f"\n正在合成最终视频 ({len(segment_files)} 段)...")
    t0 = time.time()
    used_transitions = False
    try:
        if args.no_transitions:
            raise RuntimeError("用户关闭转场，走无损拼接")
        build_video_with_transitions(clips, temp_path, args)
        used_transitions = True
        print("  转场合成完成 (xfade)。")
    except Exception as e:
        print(f"  [info] 转场不可用，回退无损拼接: {e}")
        concat_with_ffmpeg(segment_files, temp_path)

    # 混入音轨 / 封装
    try:
        mux_audio(temp_path, final_path, args, sum(c["duration_sec"] for c in clips))
    except Exception as e:
        print(f"音轨封装失败: {e}")
        # 最后兜底：直接复制临时视频
        subprocess.run(["ffmpeg", "-y", "-i", temp_path, "-c", "copy",
                        final_path], capture_output=True, text=True)
    concat_time = time.time() - t0

    if os.path.exists(temp_path):
        os.remove(temp_path)

    final_size_mb = os.path.getsize(final_path) / (1024 * 1024)
    final_size_gb = final_size_mb / 1024
    final_dur = _probe_duration(final_path)
    print(f"合成完成！({concat_time:.1f}s)")
    print(f"\n{'=' * 72}")
    print(f"最终视频: {final_path}")
    print(f"文件大小: {final_size_mb:.0f} MB ({final_size_gb:.2f} GB)")
    if final_dur:
        fm = int(final_dur // 60)
        fs = int(final_dur % 60)
        print(f"视频时长: {fm}:{fs:02d} ({final_dur:.0f}s)")
    print(f"转场: {'是' if used_transitions else '否'}  "
          f"音轨: {'环境' if args.audio else ('自备' if args.audio_file else '无')}")
    print(f"总耗时: {render_mins}:{render_secs:02d}")
    print(f"{'=' * 72}")

    # 清理断点
    if os.path.exists(checkpoint_path):
        os.remove(checkpoint_path)

    # 可选清理分段文件
    if args.cleanup:
        print("清理分段文件中...")
        for f in segment_files:
            if os.path.exists(f):
                os.remove(f)
        # 清理可能残留的标题卡
        for c in clips:
            if os.path.exists(c["out_path"]) and c["out_path"] in segment_files:
                pass
        try:
            if not os.listdir(segment_dir):
                os.rmdir(segment_dir)
        except Exception:
            pass
        print("已清理。")


if __name__ == "__main__":
    main()
