"""
影片解析度與旋轉調整模組

提供影片縮放和旋轉功能，支援 GPU/CPU 自動回退。
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..core.encoding import EncodingStrategy
from ..core.executor import FFmpegCommand, FFmpegExecutor

# 旋轉角度對應的 FFmpeg transpose 濾鏡
ROTATION_FILTERS: dict[int, list[str]] = {
    0: [],
    90: ["transpose=1"],  # 順時針 90°
    180: ["transpose=1", "transpose=1"],  # 180°
    270: ["transpose=2"],  # 逆時針 90° (= 順時針 270°)
}


@dataclass
class AdjustConfig:
    """影片調整配置"""

    input_file: Path
    output_file: Path
    width: Optional[int] = None  # None 表示不縮放
    height: Optional[int] = None  # -1 表示自動等比例
    rotation: int = 0  # 0, 90, 180, 270
    encoding: str = "libx264"
    preset: str = "medium"


class VideoAdjuster:
    """影片解析度與旋轉調整器"""

    def __init__(self, executor: FFmpegExecutor, encoding_strategy: EncodingStrategy):
        self.executor = executor
        self.encoding_strategy = encoding_strategy

    def adjust(self, config: AdjustConfig) -> tuple[bool, str]:
        """
        調整影片解析度和/或旋轉

        Args:
            config: AdjustConfig 配置

        Returns:
            tuple[bool, str]: (成功與否, 訊息)
        """
        filters = self._build_filters(config)

        if not filters:
            return False, "未指定任何調整操作（解析度或旋轉）"

        for codec in self.encoding_strategy.get_codecs(config.encoding):
            command = FFmpegCommand(
                input_files=[config.input_file],
                output_file=config.output_file,
                codec_args=["-c:v", codec, "-preset", config.preset],
                filter_args=filters,
            )
            success, message = self.executor.execute(command)

            if success:
                return True, message

            if not self.encoding_strategy.should_fallback(message):
                return False, message

        return False, "所有編碼策略均失敗"

    @staticmethod
    def _build_filters(config: AdjustConfig) -> list[str]:
        """
        建構 FFmpeg 濾鏡列表

        Args:
            config: AdjustConfig 配置

        Returns:
            list[str]: 濾鏡字串列表（傳給 -vf 用逗號連接）
        """
        filters: list[str] = []

        # 縮放濾鏡
        if config.width is not None:
            h = config.height if config.height is not None else -1
            filters.append(f"scale={config.width}:{h}")

        # 旋轉濾鏡
        rotation_filters = ROTATION_FILTERS.get(config.rotation, [])
        filters.extend(rotation_filters)

        return filters
