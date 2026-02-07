"""
影片截圖模組

提供單張截圖和批次截圖功能。
"""

from dataclasses import dataclass
from pathlib import Path

from ..core.executor import FFmpegCommand, FFmpegExecutor


@dataclass
class ScreenshotConfig:
    """單張截圖配置"""

    input_file: Path
    output_file: Path
    timestamp: str = "00:00:00"  # HH:MM:SS 或秒數
    image_format: str = "PNG"  # PNG, JPG


@dataclass
class BatchScreenshotConfig:
    """批次截圖配置"""

    input_file: Path
    output_dir: Path
    interval: int = 10  # 每 N 秒一張
    image_format: str = "PNG"  # PNG, JPG


class VideoScreenshot:
    """影片截圖器"""

    def __init__(self, executor: FFmpegExecutor):
        self.executor = executor

    def capture(self, config: ScreenshotConfig) -> tuple[bool, str]:
        """
        擷取單張截圖

        Args:
            config: ScreenshotConfig 配置

        Returns:
            tuple[bool, str]: (成功與否, 訊息)
        """
        # -frames:v 1 只擷取一幀
        codec_args = ["-frames:v", "1"]

        # JPG 需要指定編碼器
        if config.image_format.upper() == "JPG":
            codec_args.extend(["-c:v", "mjpeg", "-q:v", "2"])

        command = FFmpegCommand(
            input_files=[config.input_file],
            output_file=config.output_file,
            codec_args=codec_args,
            extra_args=["-ss", config.timestamp],
            skip_audio_copy=True,
        )
        return self.executor.execute(command)

    def capture_batch(self, config: BatchScreenshotConfig) -> tuple[bool, str]:
        """
        批次截圖（每 N 秒一張）

        Args:
            config: BatchScreenshotConfig 配置

        Returns:
            tuple[bool, str]: (成功與否, 訊息)
        """
        # 確保輸出目錄存在
        config.output_dir.mkdir(parents=True, exist_ok=True)

        ext = ".jpg" if config.image_format.upper() == "JPG" else ".png"
        output_pattern = config.output_dir / f"frame_%04d{ext}"

        # fps=1/N 表示每 N 秒一幀
        filter_args = [f"fps=1/{config.interval}"]

        codec_args: list[str] = []
        if config.image_format.upper() == "JPG":
            codec_args = ["-c:v", "mjpeg", "-q:v", "2"]

        command = FFmpegCommand(
            input_files=[config.input_file],
            output_file=output_pattern,
            codec_args=codec_args,
            filter_args=filter_args,
            skip_audio_copy=True,
        )
        return self.executor.execute(command)
