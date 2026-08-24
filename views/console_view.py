from viewmodels.generator_viewmodel import GeneratorViewModel


class ConsoleView:
    """控制台视图：绑定 ViewModel，展示进度与结果。"""

    def __init__(self):
        self.viewmodel = GeneratorViewModel()
        self.viewmodel.on_progress = self._on_progress

    def _on_progress(self, message: str):
        print(message)

    def render(self):
        print("=" * 50)
        print("故障艺术生成器 (Glitch Art Generator) 启动...")
        print("=" * 50)

        results = self.viewmodel.run_all()

        print("=" * 50)
        success = [r for r in results if r["ok"]]
        print(f"输出目录: {self.viewmodel.output_dir}")
        print(f"完成！共生成 {len(success)}/{len(results)} 张图片（文件名基于日期+哈希，不覆盖历史）。")
        for r in success:
            print(f"  - {r['name']}: {r['path']}")
        if len(success) != len(results):
            print("以下生成失败 (FAIL):")
            for r in results:
                if not r["ok"]:
                    print(f"  - {r['name']}: {r['error']}")
        print("=" * 50)
