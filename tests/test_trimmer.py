"""
影片剪輯模組測試
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ffmpeg_toolkit.core.executor import FFmpegExecutor
from ffmpeg_toolkit.features.trimmer import TrimConfig, VideoTrimmer


@pytest.fixture
def mock_executor():
    return MagicMock(spec=FFmpegExecutor)


@pytest.fixture
def trimmer(mock_executor):
    return VideoTrimmer(mock_executor)


class TestVideoTrimmer:
    def test_trim_copy_mode(self, trimmer, mock_executor):
        mock_executor.execute.return_value = (True, "處理完成")

        config = TrimConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.mp4"),
            start_time="00:01:00",
            end_time="00:02:00",
        )
        success, message = trimmer.trim(config)

        assert success is True
        cmd = mock_executor.execute.call_args[0][0]
        assert "-c" in cmd.codec_args
        assert "copy" in cmd.codec_args
        assert "-ss" in cmd.extra_args
        assert "00:01:00" in cmd.extra_args
        assert "-to" in cmd.extra_args
        assert "00:02:00" in cmd.extra_args
        assert cmd.skip_audio_copy is True

    def test_trim_reencode_mode(self, trimmer, mock_executor):
        mock_executor.execute.return_value = (True, "處理完成")

        config = TrimConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.mp4"),
            start_time="00:00:30",
            copy_mode=False,
        )
        success, message = trimmer.trim(config)

        assert success is True
        cmd = mock_executor.execute.call_args[0][0]
        assert "libx264" in cmd.codec_args

    def test_trim_no_end_time(self, trimmer, mock_executor):
        mock_executor.execute.return_value = (True, "處理完成")

        config = TrimConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.mp4"),
            start_time="00:05:00",
            end_time="",
        )
        trimmer.trim(config)

        cmd = mock_executor.execute.call_args[0][0]
        assert "-to" not in cmd.extra_args


class TestTimeValidation:
    def test_valid_hhmmss(self):
        assert VideoTrimmer.validate_time_format("01:23:45") is True

    def test_valid_hhmmss_decimal(self):
        assert VideoTrimmer.validate_time_format("00:00:30.500") is True

    def test_valid_seconds(self):
        assert VideoTrimmer.validate_time_format("90") is True

    def test_valid_seconds_decimal(self):
        assert VideoTrimmer.validate_time_format("90.5") is True

    def test_valid_empty(self):
        assert VideoTrimmer.validate_time_format("") is True

    def test_invalid_format(self):
        assert VideoTrimmer.validate_time_format("abc") is False

    def test_invalid_partial(self):
        assert VideoTrimmer.validate_time_format("01:23") is False
