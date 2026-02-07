"""
影片解析度與旋轉調整模組測試
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ffmpeg_toolkit.core.encoding import EncodingStrategy
from ffmpeg_toolkit.core.executor import FFmpegExecutor
from ffmpeg_toolkit.features.video_adjust import AdjustConfig, VideoAdjuster


@pytest.fixture
def mock_executor():
    return MagicMock(spec=FFmpegExecutor)


@pytest.fixture
def encoding_strategy():
    return EncodingStrategy()


@pytest.fixture
def adjuster(mock_executor, encoding_strategy):
    return VideoAdjuster(mock_executor, encoding_strategy)


class TestVideoAdjuster:
    def test_scale_only(self, adjuster, mock_executor):
        mock_executor.execute.return_value = (True, "處理完成")

        config = AdjustConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.mp4"),
            width=1280,
            height=-1,
        )
        success, message = adjuster.adjust(config)

        assert success is True
        cmd = mock_executor.execute.call_args[0][0]
        assert any("scale=1280:-1" in f for f in cmd.filter_args)

    def test_scale_with_height(self, adjuster, mock_executor):
        mock_executor.execute.return_value = (True, "處理完成")

        config = AdjustConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.mp4"),
            width=1920,
            height=1080,
        )
        adjuster.adjust(config)

        cmd = mock_executor.execute.call_args[0][0]
        assert any("scale=1920:1080" in f for f in cmd.filter_args)

    def test_rotate_90(self, adjuster, mock_executor):
        mock_executor.execute.return_value = (True, "處理完成")

        config = AdjustConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.mp4"),
            rotation=90,
        )
        adjuster.adjust(config)

        cmd = mock_executor.execute.call_args[0][0]
        assert "transpose=1" in cmd.filter_args

    def test_rotate_180(self, adjuster, mock_executor):
        mock_executor.execute.return_value = (True, "處理完成")

        config = AdjustConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.mp4"),
            rotation=180,
        )
        adjuster.adjust(config)

        cmd = mock_executor.execute.call_args[0][0]
        assert cmd.filter_args.count("transpose=1") == 2

    def test_rotate_270(self, adjuster, mock_executor):
        mock_executor.execute.return_value = (True, "處理完成")

        config = AdjustConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.mp4"),
            rotation=270,
        )
        adjuster.adjust(config)

        cmd = mock_executor.execute.call_args[0][0]
        assert "transpose=2" in cmd.filter_args

    def test_scale_and_rotate(self, adjuster, mock_executor):
        mock_executor.execute.return_value = (True, "處理完成")

        config = AdjustConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.mp4"),
            width=1280,
            height=-1,
            rotation=90,
        )
        adjuster.adjust(config)

        cmd = mock_executor.execute.call_args[0][0]
        assert any("scale=1280:-1" in f for f in cmd.filter_args)
        assert "transpose=1" in cmd.filter_args

    def test_no_operation_fails(self, adjuster):
        config = AdjustConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.mp4"),
        )
        success, message = adjuster.adjust(config)

        assert success is False
        assert "未指定" in message

    def test_gpu_fallback(self, adjuster, mock_executor):
        mock_executor.execute.side_effect = [
            (False, "No NVENC capable devices found"),
            (True, "處理完成"),
        ]

        config = AdjustConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.mp4"),
            width=1280,
        )
        success, message = adjuster.adjust(config)

        assert success is True
        assert mock_executor.execute.call_count == 2


class TestBuildFilters:
    def test_no_filters(self):
        config = AdjustConfig(input_file=Path("i.mp4"), output_file=Path("o.mp4"))
        assert VideoAdjuster._build_filters(config) == []

    def test_scale_auto_height(self):
        config = AdjustConfig(input_file=Path("i.mp4"), output_file=Path("o.mp4"), width=720)
        filters = VideoAdjuster._build_filters(config)
        assert filters == ["scale=720:-1"]

    def test_rotation_only(self):
        config = AdjustConfig(input_file=Path("i.mp4"), output_file=Path("o.mp4"), rotation=90)
        filters = VideoAdjuster._build_filters(config)
        assert filters == ["transpose=1"]

    def test_combined(self):
        config = AdjustConfig(input_file=Path("i.mp4"), output_file=Path("o.mp4"), width=1920, height=1080, rotation=270)
        filters = VideoAdjuster._build_filters(config)
        assert filters == ["scale=1920:1080", "transpose=2"]
