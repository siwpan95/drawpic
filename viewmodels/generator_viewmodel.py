import os

from core.image_io import save_image_from_array
from core.naming import build_filename
from core.paths import OUTPUT_DIR, ensure_output_dir
from models import ALL_GENERATORS


class GeneratorViewModel:
    """故障生成器的视图模型。

    职责：
    - 持有所需的生成器实例与输出目录（状态）
    - 编排生成流程，调用 Model 生成并保存图片（文件名基于日期+哈希，绝不覆盖）
    - 通过 on_progress 回调向 View 推送进度
    - 记录每次生成的结果（results），供 View 展示
    """

    def __init__(self, output_dir: str = None):
        self.output_dir = ensure_output_dir(output_dir or OUTPUT_DIR)
        self.generators = [g() for g in ALL_GENERATORS]
        self.results = []  # [{name, path, ok, error}, ...]
        self.on_progress = None  # 进度回调: Callable[[str], None]

    def _emit(self, message: str):
        if self.on_progress:
            self.on_progress(message)

    def run(self, generator, filename: str = None) -> dict:
        """生成单张图片并保存，返回结果字典。

        文件名默认由 core.naming.build_filename 依据「日期+哈希」生成，
        每次运行都产出全新文件，不会覆盖历史输出。
        """
        self._emit(f"正在生成: {generator.name}...")
        try:
            w, h = generator.default_size
            data = generator.generate(w, h)
            out_name = filename or build_filename(generator.default_filename)
            abs_path = save_image_from_array(
                data, os.path.join(self.output_dir, out_name)
            )
            result = {"name": generator.name, "path": abs_path, "ok": True, "error": None}
        except Exception as e:
            result = {"name": generator.name, "path": None, "ok": False, "error": str(e)}

        self.results.append(result)
        if result["ok"]:
            self._emit(f"[OK] 已生成图片: {result['path']}")
        else:
            self._emit(f"[FAIL] 生成失败: {result['name']} - {result['error']}")
        return result

    def run_all(self):
        """依次运行全部生成器，清空并重置结果列表。"""
        self.results = []
        for gen in self.generators:
            self.run(gen)
        return self.results
