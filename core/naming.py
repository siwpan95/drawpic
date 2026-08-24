import datetime
import uuid

# 图片扩展名
EXT = "png"
# 视频扩展名
EXT_VIDEO = "mp4"


def build_filename(prefix: str, ext: str = EXT) -> str:
    """生成基于「日期 + 哈希」的唯一文件名，确保后续生成不会覆盖旧文件。

    格式: {prefix}_{YYYYMMDD_HHMMSS}_{8位短哈希}.{ext}
      - 日期部分保证按时间可读排序
      - 哈希部分 (uuid) 保证同一秒内多次生成也不冲突
    """
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    short_hash = uuid.uuid4().hex[:8]
    return f"{prefix}_{ts}_{short_hash}.{ext}"


def build_video_filename(prefix: str) -> str:
    """生成视频文件名（基于日期 + 哈希，扩展名为 mp4），与 build_filename 同策略。"""
    return build_filename(prefix, EXT_VIDEO)
