"""
測試 FFmpegExecutor 執行器模組
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from ffmpeg_toolkit.core.executor import FFmpegCommand, FFmpegExecutor


class TestFFmpegCommand:
    """測試 FFmpegCommand dataclass"""

    def test_create_basic_command(self, mock_video_file, mock_output_file):
        """測試建立基本命令"""
        cmd = FFmpegCommand(
            input_files=[mock_video_file],
            output_file=mock_output_file,
            codec_args=["-c:v", "libx264", "-preset", "medium"],
            filter_args=["scale=1280:720"],
        )

        assert cmd.input_files == [mock_video_file]
        assert cmd.output_file == mock_output_file
        assert cmd.codec_args == ["-c:v", "libx264", "-preset", "medium"]
        assert cmd.filter_args == ["scale=1280:720"]
        assert cmd.timeout == 3600  # 預設 1 小時

    def test_command_with_extra_args(self, mock_video_file, mock_output_file):
        """測試含額外參數的命令"""
        cmd = FFmpegCommand(
            input_files=[mock_video_file],
            output_file=mock_output_file,
            codec_args=["-c:v", "h264_nvenc"],
            filter_args=[],
            extra_args=["-hwaccel", "cuda"],
        )

        assert cmd.extra_args == ["-hwaccel", "cuda"]


class TestFFmpegExecutor:
    """測試 FFmpegExecutor 類別"""

    def test_build_command_basic(self, mock_video_file, mock_output_file):
        """測試建立基本 FFmpeg 命令列"""
        executor = FFmpegExecutor()
        command = FFmpegCommand(
            input_files=[mock_video_file],
            output_file=mock_output_file,
            codec_args=["-c:v", "libx264", "-preset", "medium"],
            filter_args=["scale=1280:720"],
        )

        cmd_list = executor._build_command(command)

        assert cmd_list[0] == "ffmpeg"
        assert "-i" in cmd_list
        assert str(mock_video_file) in cmd_list
        assert "-c:v" in cmd_list
        assert "libx264" in cmd_list
        assert "-preset" in cmd_list
        assert "medium" in cmd_list
        assert "-vf" in cmd_list
        assert "scale=1280:720" in cmd_list
        assert "-c:a" in cmd_list
        assert "copy" in cmd_list
        assert str(mock_output_file) in cmd_list

    def test_build_command_with_extra_args(self, mock_video_file, mock_output_file):
        """測試建立含額外參數的命令"""
        executor = FFmpegExecutor()
        command = FFmpegCommand(
            input_files=[mock_video_file],
            output_file=mock_output_file,
            codec_args=["-c:v", "h264_nvenc"],
            filter_args=[],
            extra_args=["-hwaccel", "cuda"],
        )

        cmd_list = executor._build_command(command)

        assert "-hwaccel" in cmd_list
        assert "cuda" in cmd_list

    def test_log_callback(self):
        """測試日誌回呼功能"""
        log_messages = []

        def log_callback(msg):
            log_messages.append(msg)

        executor = FFmpegExecutor(log_callback=log_callback)
        executor._log("Test message")

        assert len(log_messages) == 1
        assert log_messages[0] == "Test message"

    def test_sanitize_error_removes_paths(self):
        """測試錯誤訊息清理（移除路徑）"""
        executor = FFmpegExecutor()

        error_msg = "Error opening file C:\\Users\\test\\video.mp4"
        sanitized = executor._sanitize_error(error_msg)

        assert "C:\\Users\\test\\video.mp4" not in sanitized
        assert "[PATH]" in sanitized

    def test_sanitize_error_truncates_long_messages(self):
        """測試錯誤訊息截斷"""
        executor = FFmpegExecutor()

        long_error = "A" * 600
        sanitized = executor._sanitize_error(long_error)

        assert len(sanitized) <= 550  # 500 + "... (詳細資訊請查看日誌檔案)"
        assert "詳細資訊請查看日誌檔案" in sanitized

    @patch("ffmpeg_toolkit.core.executor.subprocess.Popen")
    def test_execute_success(self, mock_popen, mock_video_file, mock_output_file):
        """測試成功執行 FFmpeg"""
        # Mock subprocess
        mock_process = MagicMock()
        mock_process.poll.return_value = 0
        mock_process.stderr.readline.side_effect = ["", None]
        mock_popen.return_value = mock_process

        executor = FFmpegExecutor()
        command = FFmpegCommand(
            input_files=[mock_video_file],
            output_file=mock_output_file,
            codec_args=["-c:v", "libx264"],
            filter_args=[],
        )

        success, message = executor.execute(command)

        assert success is True
        assert "處理完成" in message

    @patch("ffmpeg_toolkit.core.executor.subprocess.Popen")
    def test_execute_failure(self, mock_popen, mock_video_file, mock_output_file):
        """測試執行 FFmpeg 失敗"""
        # Mock subprocess with error
        mock_process = MagicMock()
        mock_process.poll.return_value = 1
        mock_process.stderr.readline.side_effect = ["Error: Invalid codec\n", ""]
        mock_popen.return_value = mock_process

        executor = FFmpegExecutor()
        command = FFmpegCommand(
            input_files=[mock_video_file],
            output_file=mock_output_file,
            codec_args=["-c:v", "invalid_codec"],
            filter_args=[],
        )

        success, message = executor.execute(command)

        assert success is False
        assert len(message) > 0

    @patch("ffmpeg_toolkit.core.executor.time.time")
    @patch("ffmpeg_toolkit.core.executor.subprocess.Popen")
    def test_execute_timeout(self, mock_popen, mock_time, mock_video_file, mock_output_file):
        """測試執行超時"""
        # Mock time to simulate timeout
        mock_time.side_effect = [0, 3601]  # Start time, then after timeout

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.stderr.readline.return_value = "processing...\n"
        mock_popen.return_value = mock_process

        executor = FFmpegExecutor()
        command = FFmpegCommand(
            input_files=[mock_video_file],
            output_file=mock_output_file,
            codec_args=["-c:v", "libx264"],
            filter_args=[],
        )

        success, message = executor.execute(command)

        assert success is False
        assert "超時" in message or "timeout" in message.lower()
        mock_process.kill.assert_called_once()
