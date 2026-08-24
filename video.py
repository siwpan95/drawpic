"""故障艺术视频生成器 —— 启动入口（图片升级为视频）。

把原有「静态故障图生成」升级为「动态故障视频生成」，复用同一套 GlitchGenerator 模型层：
每个生成器现在接受时间参数 t 与固定种子 seed，在保持结构稳定的前提下平滑运动。

用法:
  python video.py                  # 默认：合成一条「展示卷轴」MP4（所有效果轮播）
  python video.py --mode all       # 每个生成器各输出一段独立 MP4
  python video.py --name 扫描线     # 仅渲染名称包含「扫描线」的生成器
  python video.py --duration 5 --fps 30 --no-label
"""
import argparse
import os
import sys

from viewmodels.video_viewmodel import VideoViewModel


def main():
    parser = argparse.ArgumentParser(
        description="故障艺术视频生成器：把静态故障图升级为动态视频"
    )
    parser.add_argument(
        "--mode", choices=["all", "showcase"], default="showcase",
        help="all=每个生成器各一段视频；showcase=拼接成一条展示卷轴（默认）",
    )
    parser.add_argument(
        "--name", default=None,
        help="指定单个生成器（按名称包含匹配，如 --name 扫描线 / --name RGB）",
    )
    parser.add_argument("--duration", type=float, default=4.0,
                        help="单段视频时长（秒），showcase 模式下为每效果轮播时长")
    parser.add_argument("--fps", type=int, default=24, help="帧率")
    parser.add_argument("--out", default=None, help="输出目录（默认 output/）")
    parser.add_argument("--no-label", action="store_true", help="关闭画面左上角名称叠加")
    parser.add_argument("--width", type=int, default=None, help="强制帧宽（默认各生成器尺寸）")
    parser.add_argument("--height", type=int, default=None, help="强制帧高")
    args = parser.parse_args()

    vm = VideoViewModel(args.out)
    vm.on_progress = lambda m: print(m)
    label = not args.no_label

    if args.name:
        gen = next((g for g in vm.generators if args.name in g.name), None)
        if not gen:
            print(f"未找到名称包含「{args.name}」的生成器。可用：")
            for g in vm.generators:
                print(f"  - {g.name}")
            sys.exit(1)
        vm.render_generator(
            gen, duration=args.duration, fps=args.fps, label=label,
            width=args.width, height=args.height,
        )
    elif args.mode == "all":
        vm.render_all(duration=args.duration, fps=args.fps, label=label)
    else:
        vm.render_showcase(
            duration_per=args.duration, fps=args.fps, label=label,
            width=args.width or 960, height=args.height or 600,
        )

    print("=" * 50)
    success = [r for r in vm.results if r["ok"]]
    print(f"输出目录: {vm.output_dir}")
    print(f"完成！共生成 {len(success)}/{len(vm.results)} 个视频（文件名基于日期+哈希，不覆盖历史）。")
    for r in success:
        print(f"  - {r['name']}: {r['path']}")
    if len(success) != len(vm.results):
        print("以下生成失败 (FAIL):")
        for r in vm.results:
            if not r["ok"]:
                print(f"  - {r['name']}: {r['error']}")
    print("=" * 50)


if __name__ == "__main__":
    main()
