"""
測試 SubtitleBurner 字幕燒錄模組
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from ffmpeg_toolkit.core.encoding import EncodingStrategy
from ffmpeg_toolkit.core.executor import FFmpegExecutor
from ffmpeg_toolkit.features.subtitle import SubtitleBurner, SubtitleConfig, SubtitleStyle


class TestSubtitleStyle:
    """測試 SubtitleStyle dataclass"""

    def test_default_style(self):
        """測試預設樣式"""
        style = SubtitleStyle()

        assert style.font_name == "Arial"
        assert style.font_size == 24
        assert style.primary_color == "&H00FFFFFF"
        assert style.border_style == 1
        assert style.margin_v == 20

    def test_custom_style(self):
        """測試自訂樣式"""
        style = SubtitleStyle(
            font_name="微軟正黑體",
            font_size=30,
            primary_color="&H0000FF00",  # 綠色
            border_style=3,
            position_x=10,
            position_y=-5,
        )

        assert style.font_name == "微軟正黑體"
        assert style.font_size == 30
        assert style.primary_color == "&H0000FF00"
        assert style.border_style == 3
        assert style.position_x == 10
        assert style.position_y == -5


class TestSubtitleConfig:
    """測試 SubtitleConfig dataclass"""

    def test_basic_config(self, mock_video_file, mock_subtitle_file, mock_output_file):
        """測試基本配置"""
        config = SubtitleConfig(
            video_file=mock_video_file,
            subtitle_file=mock_subtitle_file,
            output_file=mock_output_file,
        )

        assert config.video_file == mock_video_file
        assert config.subtitle_file == mock_subtitle_file
        assert config.output_file == mock_output_file
        assert config.encoding == "libx264"
        assert config.preset == "medium"


class TestSubtitleBurner:
    """測試 SubtitleBurner 類別"""

    @pytest.fixture
    def mock_executor(self):
        """Mock FFmpegExecutor"""
        executor = Mock(spec=FFmpegExecutor)
        executor.log_callback = None
        executor.execute.return_value = (True, "處理完成")
        return executor

    @pytest.fixture
    def encoding_strategy(self):
        """真實的 EncodingStrategy"""
        return EncodingStrategy()

    @pytest.fixture
    def burner(self, mock_executor, encoding_strategy):
        """建立 SubtitleBurner 實例"""
        return SubtitleBurner(mock_executor, encoding_strategy)

    def test_build_subtitle_style_basic(self, burner):
        """測試建立基本字幕樣式"""
        style = SubtitleStyle()
        result = burner._build_subtitle_style(style)

        assert "Fontname=Arial" in result
        assert "Fontsize=24" in result
        assert "PrimaryColour=&H00FFFFFF" in result
        assert "BorderStyle=1" in result
        assert "MarginV=20" in result
        assert "Alignment=2" in result

    def test_build_subtitle_style_with_position(self, burner):
        """測試帶位置偏移的字幕樣式"""
        style = SubtitleStyle(position_x=10, position_y=5, margin_v=20)
        result = burner._build_subtitle_style(style)

        # X 向右偏移 -> MarginL=10, MarginR=0
        assert "MarginL=10" in result
        assert "MarginR=0" in result
        # Y 向下偏移 -> MarginV = 20 + 5 = 25
        assert "MarginV=25" in result

    def test_build_subtitle_style_negative_x(self, burner):
        """測試 X 負向偏移"""
        style = SubtitleStyle(position_x=-10, margin_v=20)
        result = burner._build_subtitle_style(style)

        # X 向左偏移 -> MarginL=0, MarginR=10
        assert "MarginL=0" in result
        assert "MarginR=10" in result

    def test_calculate_back_color(self, burner):
        """測試計算背景顏色（含透明度）"""
        # 0% 透明（完全不透明）
        result = burner._calculate_back_color(0)
        assert result == "&Hff000000"

        # 50% 透明
        result = burner._calculate_back_color(50)
        expected_alpha = int((100 - 50) * 255 / 100)
        assert result == f"&H{expected_alpha:02x}000000"

        # 100% 透明（完全透明）
        result = burner._calculate_back_color(100)
        assert result == "&H00000000"

    @patch("ffmpeg_toolkit.features.subtitle.subprocess.Popen")
    def test_detect_video_size_success(self, mock_popen, burner, mock_video_file):
        """測試成功檢測影片尺寸"""
        # Mock ffmpeg output
        mock_process = MagicMock()
        mock_process.communicate.return_value = (
            "",
            "Stream #0:0: Video: h264, 1920x1080, 30 fps",
        )
        mock_popen.return_value = mock_process

        size = burner._detect_video_size(mock_video_file)

        assert size == "1920x1080"

    @patch("ffmpeg_toolkit.features.subtitle.subprocess.Popen")
    def test_detect_video_size_timeout(self, mock_popen, burner, mock_video_file):
        """測試影片尺寸檢測超時"""
        # Mock timeout
        import subprocess

        mock_process = MagicMock()
        mock_process.communicate.side_effect = subprocess.TimeoutExpired("ffmpeg", 30)
        mock_popen.return_value = mock_process

        size = burner._detect_video_size(mock_video_file)

        # 應返回預設值
        assert size == "1920x1080"

    def test_burn_success_with_nvenc(
        self, burner, mock_executor, mock_video_file, mock_subtitle_file, mock_output_file
    ):
        """測試使用 NVENC 成功燒錄"""
        config = SubtitleConfig(
            video_file=mock_video_file,
            subtitle_file=mock_subtitle_file,
            output_file=mock_output_file,
            encoding="libx264",
            preset="medium",
        )

        with patch.object(burner, "_detect_video_size", return_value="1920x1080"):
            success, message = burner.burn(config)

        assert success is True
        assert "處理完成" in message
        # 驗證只呼叫一次（NVENC 成功）
        assert mock_executor.execute.call_count == 1

    def test_burn_fallback_to_cpu(
        self, burner, mock_executor, encoding_strategy, mock_video_file, mock_subtitle_file, mock_output_file
    ):
        """測試 NVENC 失敗後回退至 CPU"""
        # 第一次呼叫失敗（NVENC 錯誤），第二次成功（CPU）
        mock_executor.execute.side_effect = [
            (False, "Cannot load nvEncodeAPI"),
            (True, "處理完成"),
        ]

        config = SubtitleConfig(
            video_file=mock_video_file,
            subtitle_file=mock_subtitle_file,
            output_file=mock_output_file,
            encoding="libx264",
            preset="medium",
        )

        with patch.object(burner, "_detect_video_size", return_value="1920x1080"):
            success, message = burner.burn(config)

        assert success is True
        assert "處理完成" in message
        # 驗證呼叫兩次（NVENC -> CPU）
        assert mock_executor.execute.call_count == 2

    def test_burn_all_strategies_fail(
        self, burner, mock_executor, mock_video_file, mock_subtitle_file, mock_output_file
    ):
        """測試所有編碼策略都失敗"""
        # 所有編碼器都失敗
        mock_executor.execute.return_value = (False, "Unknown error")

        config = SubtitleConfig(
            video_file=mock_video_file,
            subtitle_file=mock_subtitle_file,
            output_file=mock_output_file,
            encoding="libx264",
        )

        with patch.object(burner, "_detect_video_size", return_value="1920x1080"):
            success, message = burner.burn(config)

        assert success is False
        # 驗證嘗試了兩個編碼器（NVENC 和 CPU）
        assert mock_executor.execute.call_count == 2

    def test_burn_non_nvenc_error(
        self, burner, mock_executor, mock_video_file, mock_subtitle_file, mock_output_file
    ):
        """測試非 NVENC 錯誤（不應回退）"""
        # 非 NVENC 錯誤（例如檔案不存在）
        mock_executor.execute.return_value = (False, "No such file or directory")

        config = SubtitleConfig(
            video_file=mock_video_file,
            subtitle_file=mock_subtitle_file,
            output_file=mock_output_file,
            encoding="libx264",
        )

        with patch.object(burner, "_detect_video_size", return_value="1920x1080"):
            success, message = burner.burn(config)

        assert success is False
        # 驗證只呼叫一次（不應回退）
        assert mock_executor.execute.call_count == 1
