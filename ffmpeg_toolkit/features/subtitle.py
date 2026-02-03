"""
字幕燒錄功能模組

此模組提供字幕燒錄業務邏輯，包含樣式配置、影片尺寸檢測和 FFmpeg 處理。
"""

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..core.encoding import EncodingStrategy
from ..core.executor import FFmpegCommand, FFmpegExecutor


@dataclass
class SubtitleStyle:
    """字幕樣式配置"""

    font_name: str = "Arial"
    font_size: int = 24
    primary_color: str = "&H00FFFFFF"  # 白色 (BGR 格式)
    back_color: str = "&H80000000"  # 半透明黑色背景
    outline_color: str = "&H00000000"  # 黑色外框
    border_style: int = 1  # 1=外框, 3=不透明背景, 0=無邊框, 4=陰影
    transparency: int = 0  # 0-100 (0=不透明, 100=完全透明)
    margin_v: int = 20  # 垂直邊距
    position_x: int = 0  # X 座標偏移
    position_y: int = 0  # Y 座標偏移
    outline_width: int = 1  # 外框寬度
    alignment: int = 2  # 2=底部居中


@dataclass
class SubtitleConfig:
    """字幕燒錄配置"""

    video_file: Path
    subtitle_file: Path
    output_file: Path
    style: SubtitleStyle = field(default_factory=SubtitleStyle)
    encoding: str = "libx264"  # 編碼器：libx264, libx265, h264_nvenc, hevc_nvenc
    preset: str = "medium"  # 編碼品質：ultrafast ~ veryslow
    extra_args: list[str] = field(default_factory=list)  # 額外 FFmpeg 參數


class SubtitleBurner:
    """
    字幕燒錄器

    提供字幕燒錄業務邏輯，支援 GPU/CPU 編碼自動回退。
    """

    def __init__(self, executor: FFmpegExecutor, encoding_strategy: EncodingStrategy):
        """
        初始化字幕燒錄器

        Args:
            executor: FFmpegExecutor 實例
            encoding_strategy: EncodingStrategy 實例
        """
        self.executor = executor
        self.encoding_strategy = encoding_strategy

    def burn(self, config: SubtitleConfig, working_dir: Optional[Path] = None) -> tuple[bool, str]:
        """
        燒錄字幕到影片

        Args:
            config: SubtitleConfig 配置
            working_dir: 可選的工作目錄

        Returns:
            tuple[bool, str]: (成功與否, 訊息)
        """
        # 檢測影片尺寸
        video_size = self._detect_video_size(config.video_file)

        # 建立字幕樣式字串
        subtitle_style = self._build_subtitle_style(config.style)

        # 計算背景顏色（包含透明度）
        back_color = self._calculate_back_color(config.style.transparency)

        # 嘗試各個編碼器（GPU 優先，CPU 回退）
        for codec in self.encoding_strategy.get_codecs(config.encoding):
            # 建立 FFmpeg 命令
            command = self._create_ffmpeg_command(
                config=config,
                codec=codec,
                subtitle_style=subtitle_style,
                back_color=back_color,
                video_size=video_size,
                working_dir=working_dir,
            )

            # 執行 FFmpeg
            success, message = self.executor.execute(command, cwd=working_dir)

            if success:
                return True, message

            # 檢查是否為 NVENC 錯誤（需要回退）
            if not self.encoding_strategy.should_fallback(message):
                # 非 NVENC 錯誤，直接返回失敗
                return False, message

            # NVENC 錯誤，繼續嘗試下一個編碼器（CPU）

        # 所有編碼策略都失敗
        return False, "所有編碼策略均失敗，請查看日誌"

    def _detect_video_size(self, video_path: Path) -> str:
        """
        檢測影片解析度

        Args:
            video_path: 影片檔案路徑

        Returns:
            str: 影片尺寸字串（例如 "1920x1080"）
        """
        cmd = ["ffmpeg", "-i", str(video_path), "-hide_banner"]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            # 等待最多 30 秒
            _, stderr = process.communicate(timeout=30)

            # 在包含 "Video:" 的行中搜尋解析度
            for line in stderr.splitlines():
                if "Video:" in line:
                    size_match = re.search(r"(\d{2,5})x(\d{2,5})", line)
                    if size_match:
                        video_size = size_match.group(0)
                        if self.executor.log_callback:
                            self.executor.log_callback(f"檢測到影片尺寸: {video_size}")
                        return video_size

        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            if self.executor.log_callback:
                self.executor.log_callback("影片尺寸偵測超時，使用預設值 1920x1080")

        except Exception as e:
            if self.executor.log_callback:
                self.executor.log_callback(f"影片尺寸偵測失敗: {e}，使用預設值")

        # 預設值
        return "1920x1080"

    def _build_subtitle_style(self, style: SubtitleStyle) -> str:
        """
        建立 ASS 格式字幕樣式字串

        Args:
            style: SubtitleStyle 配置

        Returns:
            str: ASS 樣式字串
        """
        # 計算邊距調整（Y 座標向下偏移時增加底部邊距）
        margin_v_adjusted = style.margin_v + style.position_y if style.position_y >= 0 else style.margin_v
        margin_l = max(0, style.position_x)
        margin_r = max(0, -style.position_x)

        # 組織樣式參數
        style_params = {
            "Fontname": style.font_name,
            "Fontsize": style.font_size,
            "PrimaryColour": style.primary_color,
            "BackColour": style.back_color,
            "BorderStyle": style.border_style,
            "Outline": style.outline_width,
            "MarginV": margin_v_adjusted,
            "MarginL": margin_l,
            "MarginR": margin_r,
            "Alignment": style.alignment,
        }

        return ",".join(f"{k}={v}" for k, v in style_params.items())

    def _calculate_back_color(self, transparency: int) -> str:
        """
        計算背景顏色（包含透明度）

        Args:
            transparency: 透明度百分比 (0-100)

        Returns:
            str: ASS 格式背景顏色字串
        """
        alpha = int((100 - transparency) * 255 / 100)
        return f"&H{alpha:02x}000000"

    def _create_ffmpeg_command(
        self,
        config: SubtitleConfig,
        codec: str,
        subtitle_style: str,
        back_color: str,
        video_size: str,
        working_dir: Optional[Path],
    ) -> FFmpegCommand:
        """
        建立 FFmpeg 命令

        Args:
            config: SubtitleConfig 配置
            codec: 編碼器名稱
            subtitle_style: 字幕樣式字串
            back_color: 背景顏色
            video_size: 影片尺寸
            working_dir: 工作目錄

        Returns:
            FFmpegCommand: FFmpeg 命令物件
        """
        # 更新樣式中的背景顏色
        updated_style = config.style
        updated_style.back_color = back_color

        # 準備字幕檔案路徑
        # 如果有工作目錄，使用相對路徑（檔案名稱）
        if working_dir:
            subtitle_path = config.subtitle_file.name
        else:
            subtitle_path = str(config.subtitle_file)

        # 建立濾鏡參數
        filter_args = [f"subtitles='{subtitle_path}':force_style='{subtitle_style}':original_size={video_size}"]

        # 建立命令
        return FFmpegCommand(
            input_files=[config.video_file],
            output_file=config.output_file,
            codec_args=["-c:v", codec, "-preset", config.preset],
            filter_args=filter_args,
            extra_args=config.extra_args,
        )
