"""
影片資訊查看模組

使用 ffprobe 讀取並顯示媒體檔案的詳細資訊。
"""

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class MediaInfo:
    """媒體資訊"""

    format_name: str
    duration: float  # 秒
    size: int  # bytes
    bit_rate: int  # bps
    streams: list[dict] = field(default_factory=list)


class MediaInfoReader:
    """使用 ffprobe 讀取媒體資訊"""

    def read(self, file_path: Path) -> tuple[bool, Optional[MediaInfo], str]:
        """
        讀取媒體資訊

        Args:
            file_path: 媒體檔案路徑

        Returns:
            tuple[bool, Optional[MediaInfo], str]: (成功, 資訊, 錯誤訊息)
        """
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(file_path),
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode != 0:
                return False, None, f"ffprobe 錯誤: {result.stderr[:200]}"

            data = json.loads(result.stdout)
            fmt = data.get("format", {})
            info = MediaInfo(
                format_name=fmt.get("format_long_name", "未知"),
                duration=float(fmt.get("duration", 0)),
                size=int(fmt.get("size", 0)),
                bit_rate=int(fmt.get("bit_rate", 0)),
                streams=data.get("streams", []),
            )
            return True, info, ""
        except json.JSONDecodeError as e:
            return False, None, f"JSON 解析錯誤: {e}"
        except subprocess.TimeoutExpired:
            return False, None, "ffprobe 執行超時"
        except Exception as e:
            return False, None, str(e)

    def format_info(self, info: MediaInfo) -> str:
        """
        格式化顯示媒體資訊

        Args:
            info: MediaInfo 物件

        Returns:
            str: 格式化後的資訊字串
        """
        lines = []
        lines.append(f"格式: {info.format_name}")

        minutes, seconds = divmod(info.duration, 60)
        hours, minutes = divmod(minutes, 60)
        lines.append(f"時長: {int(hours):02d}:{int(minutes):02d}:{seconds:05.2f}")

        size_mb = info.size / (1024 * 1024)
        lines.append(f"大小: {size_mb:.2f} MB")

        bitrate_kbps = info.bit_rate / 1000
        lines.append(f"位元率: {bitrate_kbps:.0f} kbps")
        lines.append("")

        for i, stream in enumerate(info.streams):
            codec_type = stream.get("codec_type", "unknown")
            codec_name = stream.get("codec_name", "unknown")

            if codec_type == "video":
                w = stream.get("width", "?")
                h = stream.get("height", "?")
                fps_str = stream.get("r_frame_rate", "?")
                try:
                    num, den = fps_str.split("/")
                    fps = round(int(num) / int(den), 2)
                except (ValueError, ZeroDivisionError):
                    fps = fps_str
                lines.append(f"影片串流 #{i}: {codec_name} | {w}x{h} | {fps} fps")
            elif codec_type == "audio":
                sample_rate = stream.get("sample_rate", "?")
                channels = stream.get("channels", "?")
                lines.append(f"音訊串流 #{i}: {codec_name} | {sample_rate} Hz | {channels} ch")
            elif codec_type == "subtitle":
                lines.append(f"字幕串流 #{i}: {codec_name}")
            else:
                lines.append(f"串流 #{i}: {codec_type} / {codec_name}")

        return "\n".join(lines)
