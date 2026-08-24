import os

# 项目根目录 (\drawpic)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 默认输出目录：\drawpic\output
OUTPUT_DIR = os.path.join(ROOT_DIR, "output")


def resolve_path(path: str) -> str:
    """将相对路径解析为基于项目根目录的绝对路径；已是绝对路径则原样返回。"""
    if os.path.isabs(path):
        return path
    return os.path.join(ROOT_DIR, path)


def ensure_output_dir(output_dir: str = None) -> str:
    """确保输出目录存在，返回绝对路径。"""
    target = output_dir or OUTPUT_DIR
    os.makedirs(target, exist_ok=True)
    return target
