"""
影片截圖模組測試
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ffmpeg_toolkit.core.executor import FFmpegExecutor
from ffmpeg_toolkit.features.screenshot import (
    BatchScreenshotConfig,
    ScreenshotConfig,
    VideoScreenshot,
)


@pytest.fixture
def mock_executor():
    return MagicMock(spec=FFmpegExecutor)


@pytest.fixture
def screenshot(mock_executor):
    return VideoScreenshot(mock_executor)


class TestVideoScreenshot:
    def test_capture_png(self, screenshot, mock_executor):
        mock_executor.execute.return_value = (True, "處理完成")

        config = ScreenshotConfig(
            input_file=Path("input.mp4"),
            output_file=Path("screenshot.png"),
            timestamp="00:01:30",
        )
        success, message = screenshot.capture(config)

        assert success is True
        cmd = mock_executor.execute.call_args[0][0]
        assert "-frames:v" in cmd.codec_args
        assert "1" in cmd.codec_args
        assert "-ss" in cmd.extra_args
        assert "00:01:30" in cmd.extra_args
        assert cmd.skip_audio_copy is True

    def test_capture_jpg(self, screenshot, mock_executor):
        mock_executor.execute.return_value = (True, "處理完成")

        config = ScreenshotConfig(
            input_file=Path("input.mp4"),
            output_file=Path("screenshot.jpg"),
            timestamp="00:00:10",
            image_format="JPG",
        )
        screenshot.capture(config)

        cmd = mock_executor.execute.call_args[0][0]
        assert "mjpeg" in cmd.codec_args
        assert "-q:v" in cmd.codec_args

    def test_capture_batch_png(self, screenshot, mock_executor, tmp_path):
        mock_executor.execute.return_value = (True, "處理完成")

        config = BatchScreenshotConfig(
            input_file=Path("input.mp4"),
            output_dir=tmp_path / "frames",
            interval=10,
            image_format="PNG",
        )
        success, message = screenshot.capture_batch(config)

        assert success is True
        assert (tmp_path / "frames").exists()

        cmd = mock_executor.execute.call_args[0][0]
        assert any("fps=1/10" in f for f in cmd.filter_args)
        assert cmd.skip_audio_copy is True

    def test_capture_batch_jpg(self, screenshot, mock_executor, tmp_path):
        mock_executor.execute.return_value = (True, "處理完成")

        config = BatchScreenshotConfig(
            input_file=Path("input.mp4"),
            output_dir=tmp_path / "frames",
            interval=5,
            image_format="JPG",
        )
        screenshot.capture_batch(config)

        cmd = mock_executor.execute.call_args[0][0]
        assert "mjpeg" in cmd.codec_args
        assert ".jpg" in str(cmd.output_file)

    def test_capture_batch_creates_dir(self, screenshot, mock_executor, tmp_path):
        mock_executor.execute.return_value = (True, "處理完成")

        output_dir = tmp_path / "new_dir" / "frames"
        config = BatchScreenshotConfig(
            input_file=Path("input.mp4"),
            output_dir=output_dir,
            interval=10,
        )
        screenshot.capture_batch(config)

        assert output_dir.exists()

    def test_capture_failure(self, screenshot, mock_executor):
        mock_executor.execute.return_value = (False, "FFmpeg error")

        config = ScreenshotConfig(
            input_file=Path("input.mp4"),
            output_file=Path("screenshot.png"),
        )
        success, message = screenshot.capture(config)

        assert success is False
