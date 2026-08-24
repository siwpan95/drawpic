"""故障艺术生成器 —— tkinter GUI 主入口。

把原有「控制台入口」(ConsoleView) 与「视频入口」(video.py) 整合为一个图形界面：
  - 左侧列出全部 21 个生成器（故障艺术 + 网络美学），可多选
  - 模式：图片（静态 PNG） / 视频（动态 MP4）
  - 视频参数：时长、帧率、统一分辨率、名称叠加、合成方式（独立视频 / 展示卷轴）
  - 输出目录可选，生成在后台线程进行，进度实时回显，可一键打开输出文件夹

架构仍为 MVVM：界面只负责编排，真正生成复用
  - viewmodels.generator_viewmodel.GeneratorViewModel  （图片）
  - viewmodels.video_viewmodel.VideoViewModel          （视频）
"""
import os
import queue
import threading

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from core.paths import OUTPUT_DIR
from models import ALL_GENERATORS
from viewmodels.generator_viewmodel import GeneratorViewModel
from viewmodels.video_viewmodel import VideoViewModel

SENT_DONE = "<<DONE>>"


class GlitchApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("故障艺术生成器  Glitch Art Generator (GUI)")
        self.root.geometry("820x620")
        try:
            self.root.tk.call("tk", "scaling", 1.2)
        except Exception:
            pass

        self.queue = queue.Queue()
        self.generators = [g() for g in ALL_GENERATORS]  # 与列表框顺序一致

        self.mode_var = tk.StringVar(value="image")
        self.video_mode_var = tk.StringVar(value="showcase")
        self.label_var = tk.BooleanVar(value=True)
        self.out_var = tk.StringVar(value=OUTPUT_DIR)
        self.dur_var = tk.StringVar(value="4")
        self.fps_var = tk.StringVar(value="24")
        self.w_var = tk.StringVar(value="960")
        self.h_var = tk.StringVar(value="600")

        self._build_ui()
        self._poll()

    # ---- UI 构建 --------------------------------------------------------
    def _build_ui(self):
        # 顶部标题
        ttk.Label(self.root, text="故障艺术生成器 · 图片 / 视频 一体化",
                  font=("Microsoft YaHei", 14, "bold")).pack(pady=(8, 2))

        body = ttk.Frame(self.root)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        # 左：生成器列表
        left = ttk.LabelFrame(body, text="生成器（可多选，Ctrl/Shift 辅助选择）")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.listbox = tk.Listbox(left, selectmode=tk.EXTENDED, height=22)
        for gen in self.generators:
            self.listbox.insert(tk.END, gen.name)
        self.listbox.select_set(0, tk.END)  # 默认全选
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        btn_row = ttk.Frame(left)
        btn_row.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(btn_row, text="全选", command=lambda: self.listbox.selection_set(0, tk.END)).pack(side=tk.LEFT, expand=True)
        ttk.Button(btn_row, text="清空", command=lambda: self.listbox.selection_clear(0, tk.END)).pack(side=tk.LEFT, expand=True)

        # 右：参数
        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        # 模式
        mode_f = ttk.LabelFrame(right, text="生成模式")
        mode_f.pack(fill=tk.X, pady=4)
        ttk.Radiobutton(mode_f, text="图片（静态 PNG）", variable=self.mode_var,
                        value="image", command=self._on_mode_change).pack(anchor=tk.W, padx=6)
        ttk.Radiobutton(mode_f, text="视频（动态 MP4）", variable=self.mode_var,
                        value="video", command=self._on_mode_change).pack(anchor=tk.W, padx=6)

        # 视频参数
        self.video_f = ttk.LabelFrame(right, text="视频参数")
        self.video_f.pack(fill=tk.X, pady=4)
        row1 = ttk.Frame(self.video_f)
        row1.pack(fill=tk.X, padx=6, pady=2)
        ttk.Label(row1, text="时长(s)").pack(side=tk.LEFT)
        ttk.Spinbox(row1, from_=1, to=60, width=6, textvariable=self.dur_var).pack(side=tk.LEFT, padx=4)
        ttk.Label(row1, text="帧率").pack(side=tk.LEFT, padx=(10, 0))
        ttk.Spinbox(row1, from_=1, to=60, width=6, textvariable=self.fps_var).pack(side=tk.LEFT, padx=4)

        row2 = ttk.Frame(self.video_f)
        row2.pack(fill=tk.X, padx=6, pady=2)
        ttk.Label(row2, text="分辨率(WxH)").pack(side=tk.LEFT)
        ttk.Entry(row2, width=6, textvariable=self.w_var).pack(side=tk.LEFT, padx=4)
        ttk.Label(row2, text="x").pack(side=tk.LEFT)
        ttk.Entry(row2, width=6, textvariable=self.h_var).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(row2, text="叠加名称", variable=self.label_var).pack(side=tk.LEFT, padx=(10, 0))

        row3 = ttk.Frame(self.video_f)
        row3.pack(fill=tk.X, padx=6, pady=2)
        ttk.Radiobutton(row3, text="多选取时合并为展示卷轴", variable=self.video_mode_var,
                        value="showcase").pack(anchor=tk.W)
        ttk.Radiobutton(row3, text="多选取时各生成独立视频", variable=self.video_mode_var,
                        value="separate").pack(anchor=tk.W)

        # 输出目录
        out_f = ttk.LabelFrame(right, text="输出目录")
        out_f.pack(fill=tk.X, pady=4)
        orow = ttk.Frame(out_f)
        orow.pack(fill=tk.X, padx=6, pady=4)
        ttk.Entry(orow, textvariable=self.out_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(orow, text="浏览", command=self._choose_dir).pack(side=tk.LEFT, padx=4)
        ttk.Button(orow, text="打开", command=self._open_dir).pack(side=tk.LEFT)

        # 进度条 + 百分比
        prog_row = ttk.Frame(right)
        prog_row.pack(fill=tk.X, pady=4)
        self.progress = ttk.Progressbar(prog_row, mode="determinate", maximum=100, value=0)
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.pct_var = tk.StringVar(value="0%")
        ttk.Label(prog_row, textvariable=self.pct_var, width=6,
                  anchor=tk.E, font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=4)

        # 日志
        log_f = ttk.LabelFrame(right, text="进度 / 日志")
        log_f.pack(fill=tk.BOTH, expand=True, pady=4)
        self.log = scrolledtext.ScrolledText(log_f, height=10, state=tk.DISABLED)
        self.log.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # 生成按钮
        self.gen_btn = ttk.Button(self.root, text="生成", command=self._on_generate)
        self.gen_btn.pack(pady=(0, 8))

        self._on_mode_change()

    # ---- 交互 ----------------------------------------------------------
    def _on_mode_change(self):
        # 视频参数面板始终可见；分辨率仅对视频（尤其展示卷轴）生效，图片模式忽略。
        # 这里仅用于在切换时给出提示，无需显隐控件。
        pass

    def _choose_dir(self):
        d = filedialog.askdirectory(initialdir=self.out_var.get() or OUTPUT_DIR)
        if d:
            self.out_var.set(d)

    def _open_dir(self):
        path = self.out_var.get() or OUTPUT_DIR
        try:
            os.startfile(path)
        except Exception:
            messagebox.showinfo("打开文件夹", f"路径：{path}")

    def _selected(self):
        return [self.generators[i] for i in self.listbox.curselection()]

    def _res(self):
        try:
            w = int(self.w_var.get().strip())
            h = int(self.h_var.get().strip())
            if w > 0 and h > 0:
                return w, h
        except Exception:
            pass
        return None, None

    def _on_generate(self):
        selected = self._selected()
        if not selected:
            messagebox.showwarning("提示", "请至少选择一个生成器。")
            return
        self.gen_btn.configure(state=tk.DISABLED)
        self.progress.configure(mode="determinate", maximum=100, value=0)
        self.pct_var.set("0%")
        self._log(f"开始生成（模式：{self.mode_var.get()}，共 {len(selected)} 个）...")
        t = threading.Thread(target=self._worker, args=(selected,), daemon=True)
        t.start()

    def _worker(self, selected):
        out = self.out_var.get() or None
        mode = self.mode_var.get()
        try:
            if mode == "image":
                self._run_images(selected, out)
            else:
                self._run_videos(selected, out)
        except Exception as e:
            self.queue.put(f"[ERROR] {e}")
        self.queue.put(SENT_DONE)

    def _run_images(self, selected, out):
        vm = GeneratorViewModel(out)
        vm.on_progress = self._progress
        vm.results = []
        total = len(selected)
        for i, gen in enumerate(selected, 1):
            self.queue.put(f"[{i}/{total}] {gen.name}")
            vm.run(gen)
            self.queue.put(("FRAC", i / total))
        ok = [r for r in vm.results if r["ok"]]
        self.queue.put(f"图片生成完成：{len(ok)}/{total} 张 -> {vm.output_dir}")

    def _run_videos(self, selected, out):
        vm = VideoViewModel(out)
        vm.on_progress = self._progress
        vm.on_fraction = lambda f: self.queue.put(("FRAC", f))
        dur = self._to_float(self.dur_var.get(), 4.0)
        fps = self._to_int(self.fps_var.get(), 24)
        label = self.label_var.get()
        w, h = self._res()
        if len(selected) == 1:
            vm.render_generator(selected[0], duration=dur, fps=fps, label=label,
                                width=w, height=h)
            ok = [r for r in vm.results if r["ok"]]
            self.queue.put(f"视频生成完成：{len(ok)}/{len(selected)} 个 -> {vm.output_dir}")
        elif self.video_mode_var.get() == "showcase":
            if w is None or h is None:
                w, h = 960, 600
            vm.render_showcase(duration_per=dur, fps=fps, label=label,
                               width=w, height=h, generators=selected)
            ok = [r for r in vm.results if r["ok"]]
            self.queue.put(
                f"视频生成完成：1 个展示卷轴（含 {len(selected)} 个效果）"
                f"-> {vm.output_dir}" if ok else "视频生成失败"
            )
        else:
            for gen in selected:
                vm.render_generator(gen, duration=dur, fps=fps, label=label)
            ok = [r for r in vm.results if r["ok"]]
            self.queue.put(f"视频生成完成：{len(ok)}/{len(selected)} 个独立视频 -> {vm.output_dir}")

    # ---- 线程安全回显 --------------------------------------------------
    def _progress(self, msg):
        self.queue.put(msg)

    def _log(self, msg):
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _poll(self):
        try:
            while True:
                msg = self.queue.get_nowait()
                if isinstance(msg, tuple) and msg[0] == "FRAC":
                    pct = int(round(msg[1] * 100))
                    self.progress.configure(value=pct)
                    self.pct_var.set(f"{pct}%")
                elif msg == SENT_DONE:
                    self.progress.configure(value=100)
                    self.pct_var.set("100%")
                    self.gen_btn.configure(state=tk.NORMAL)
                elif msg.startswith("[ERROR]"):
                    self._log(msg)
                    messagebox.showerror("错误", msg[7:].strip())
                else:
                    self._log(msg)
        except queue.Empty:
            pass
        self.root.after(80, self._poll)

    @staticmethod
    def _to_float(s, default):
        try:
            return float(s)
        except Exception:
            return default

    @staticmethod
    def _to_int(s, default):
        try:
            return int(s)
        except Exception:
            return default


def main():
    root = tk.Tk()
    GlitchApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
