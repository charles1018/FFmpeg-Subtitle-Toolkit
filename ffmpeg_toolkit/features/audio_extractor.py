"""
音訊提取模組

提供從影片中提取音訊的功能，支援多種音訊格式。
"""

from dataclasses import dataclass
from pathlib import Path

from ..core.executor import FFmpegCommand, FFmpegExecutor

AUDIO_FORMATS: dict[str, dict] = {
    "MP3": {"ext": ".mp3", "codec": "libmp3lame", "extra": ["-q:a", "2"]},
    "AAC": {"ext": ".aac", "codec": "aac", "extra": ["-b:a", "192k"]},
    "FLAC": {"ext": ".flac", "codec": "flac", "extra": []},
    "WAV": {"ext": ".wav", "codec": "pcm_s16le", "extra": []},
}


@dataclass
class AudioExtractConfig:
    """音訊提取配置"""

    input_file: Path
    output_file: Path
    audio_format: str = "MP3"  # MP3, AAC, FLAC, WAV


class AudioExtractor:
    """音訊提取器"""

    def __init__(self, executor: FFmpegExecutor):
        self.executor = executor

    def extract(self, config: AudioExtractConfig) -> tuple[bool, str]:
        """
        從影片中提取音訊

        Args:
            config: AudioExtractConfig 配置

        Returns:
            tuple[bool, str]: (成功與否, 訊息)
        """
        fmt = AUDIO_FORMATS.get(config.audio_format)
        if not fmt:
            return False, f"不支援的音訊格式: {config.audio_format}"

        codec_args = ["-vn", "-c:a", fmt["codec"]] + fmt["extra"]

        command = FFmpegCommand(
            input_files=[config.input_file],
            output_file=config.output_file,
            codec_args=codec_args,
            skip_audio_copy=True,
        )
        return self.executor.execute(command)
