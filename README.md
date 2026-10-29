> 📦 **已归档（Archived — 仅作参考）**
> 本仓库已收入归档仓 **media-prototypes**（代码与完整 git 历史一并迁入，原仓冻结不再开发）。
> 历史分支见归档仓的 `archive/drawpic` 分支；活跃维护请前往 **media-prototypes**。
> _This repo is archived into media-prototypes; development continues there. Do not commit here._

# drawpic

> 仓库：<https://gitee.com/siwpan/drawpic> ｜ 许可：MIT（见 [LICENSE](LICENSE)）

故障艺术生成器 —— 集 21 个「故障艺术 + 网络美学」生成器于一体的 Tkinter 图形界面，支持静态 PNG 图片与动态 MP4 视频生成。

## 语言 / 类型
- Python（Tkinter GUI，MVVM 架构：models / viewmodels / views）

## 目录要点
- `main.py` —— GUI 主入口（多选生成器、图片/视频双模式、后台线程 + 进度回显）
- `longplay.py` —— 长时生成/演示脚本；`video.py` —— 视频入口
- `models/` —— 全部生成器定义；`viewmodels/` —— 图片/视频视图模型
- `views/` —— 视图层；`core/` —— 路径等基础设施；`output/` —— 输出目录

## 运行方式与依赖
- 运行：`python main.py`
- 依赖：`numpy`、`Pillow`，视频模式需 `imageio` + `imageio-ffmpeg`（提供 ffmpeg 二进制）；tkinter 为标准库。详见 `requirements.txt`。

## 测试状态
- `py_compile` 语法检查通过（38 个 .py 文件）。
- GUI 程序，本次仅编译未运行。
