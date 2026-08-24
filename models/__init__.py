"""模型层：故障艺术生成算法。每个算法是一个独立的 GlitchGenerator。"""
from .base import GlitchGenerator
from .math_glitch import MathGlitchGenerator
from .crystal_glitch import CrystalGlitchGenerator
from .red_glitch import RedGlitchGenerator
from .rgb_split import RGBSplitGenerator
from .block_glitch import BlockGlitchGenerator
from .scanline_glitch import ScanlineGlitchGenerator
from .pixel_sort import PixelSortGenerator
from .vhs_noise import VHSNoiseGenerator
from .tile_jitter import TileJitterGenerator
from .melt_glitch import MeltGlitchGenerator
from .slash_glitch import SlashGlitchGenerator
from .screen_death_glitch import ScreenDeathGlitchGenerator
from .vaporwave_glitch import VaporwaveGlitchGenerator
from .face_draw import FaceDrawGenerator
from .backrooms import BackroomsGenerator
from .liminal import LiminalSpaceGenerator
from .dreamcore import DreamcoreGenerator
from .chinese_dreamcore import ChineseDreamcoreGenerator
from .poolcore import PoolcoreGenerator
from .weirdcore import WeirdcoreGenerator
from .foodcore import FoodcoreGenerator

# 全部生成器类（注册表），ViewModel 据此实例化
ALL_GENERATORS = [
    MathGlitchGenerator,
    CrystalGlitchGenerator,
    RedGlitchGenerator,
    RGBSplitGenerator,
    BlockGlitchGenerator,
    ScanlineGlitchGenerator,
    PixelSortGenerator,
    VHSNoiseGenerator,
    TileJitterGenerator,
    MeltGlitchGenerator,
    SlashGlitchGenerator,
    ScreenDeathGlitchGenerator,
    VaporwaveGlitchGenerator,
    FaceDrawGenerator,
    # 网络美学拓展：后室 / 阈限空间 / 梦核 / 中式梦核 / 池核 / 怪核 / 食核
    BackroomsGenerator,
    LiminalSpaceGenerator,
    DreamcoreGenerator,
    ChineseDreamcoreGenerator,
    PoolcoreGenerator,
    WeirdcoreGenerator,
    FoodcoreGenerator,
]

__all__ = [
    "GlitchGenerator",
    "MathGlitchGenerator",
    "CrystalGlitchGenerator",
    "RedGlitchGenerator",
    "RGBSplitGenerator",
    "BlockGlitchGenerator",
    "ScanlineGlitchGenerator",
    "PixelSortGenerator",
    "VHSNoiseGenerator",
    "TileJitterGenerator",
    "MeltGlitchGenerator",
    "SlashGlitchGenerator",
    "ScreenDeathGlitchGenerator",
    "VaporwaveGlitchGenerator",
    "FaceDrawGenerator",
    "BackroomsGenerator",
    "LiminalSpaceGenerator",
    "DreamcoreGenerator",
    "ChineseDreamcoreGenerator",
    "PoolcoreGenerator",
    "WeirdcoreGenerator",
    "FoodcoreGenerator",
    "ALL_GENERATORS",
]
