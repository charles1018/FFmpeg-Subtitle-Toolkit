"""
影片剪輯模組

提供影片裁切功能，支援指定起止時間截取片段。
"""

import re
from dataclasses import dataclass
from pathlib import Path

from ..core.executor import FFmpegCommand, FFmpegExecutor


@dataclass
class TrimConfig:
    """影片剪輯配置"""

    input_file: Path
    output_file: Path
    start_time: str = "00:00:00"  # HH:MM:SS 或秒數
    end_time: str = ""  # 空字串表示到結尾
    copy_mode: bool = True  # True=不重編碼(快速), False=重編碼(精確)


class VideoTrimmer:
    """影片剪輯器"""

    def __init__(self, executor: FFmpegExecutor):
        self.executor = executor

    def trim(self, config: TrimConfig) -> tuple[bool, str]:
        """
        剪輯影片

        Args:
            config: TrimConfig 配置

        Returns:
            tuple[bool, str]: (成功與否, 訊息)
        """
        if config.copy_mode:
            codec_args = ["-c", "copy"]
        else:
            codec_args = ["-c:v", "libx264", "-preset", "medium", "-c:a", "aac"]

        extra_args = ["-ss", config.start_time]
        if config.end_time:
            extra_args.extend(["-to", config.end_time])

        command = FFmpegCommand(
            input_files=[config.input_file],
            output_file=config.output_file,
            codec_args=codec_args,
            extra_args=extra_args,
            skip_audio_copy=True,
        )
        return self.executor.execute(command)

    @staticmethod
    def validate_time_format(time_str: str) -> bool:
        """
        驗證時間格式

        支援 HH:MM:SS、HH:MM:SS.mmm、純秒數

        Args:
            time_str: 時間字串

        Returns:
            bool: 格式正確返回 True
        """
        if not time_str:
            return True
        if re.match(r"^\d+(\.\d+)?$", time_str):
            return True
        if re.match(r"^\d{1,2}:\d{2}:\d{2}(\.\d+)?$", time_str):
            return True
        return False
