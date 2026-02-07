"""
影片轉換模組

提供影片格式轉換和編碼轉換功能，支援 GPU/CPU 自動回退。
"""

from dataclasses import dataclass
from pathlib import Path

from ..core.encoding import EncodingStrategy
from ..core.executor import FFmpegCommand, FFmpegExecutor


@dataclass
class ConvertConfig:
    """影片轉換配置"""

    input_file: Path
    output_file: Path
    encoding: str = "libx264"  # 編碼器
    preset: str = "medium"  # 編碼速度
    crf: int = 23  # 品質 (0-51, 越低越好)


class VideoConverter:
    """影片轉換器，支援格式和編碼轉換"""

    def __init__(self, executor: FFmpegExecutor, encoding_strategy: EncodingStrategy):
        self.executor = executor
        self.encoding_strategy = encoding_strategy

    def convert(self, config: ConvertConfig) -> tuple[bool, str]:
        """
        轉換影片格式/編碼

        Args:
            config: ConvertConfig 配置

        Returns:
            tuple[bool, str]: (成功與否, 訊息)
        """
        for codec in self.encoding_strategy.get_codecs(config.encoding):
            codec_args = ["-c:v", codec, "-preset", config.preset, "-crf", str(config.crf)]
            command = FFmpegCommand(
                input_files=[config.input_file],
                output_file=config.output_file,
                codec_args=codec_args,
            )
            success, message = self.executor.execute(command)

            if success:
                return True, message

            if not self.encoding_strategy.should_fallback(message):
                return False, message

        return False, "所有編碼策略均失敗"
