"""
影片轉換模組測試
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ffmpeg_toolkit.core.encoding import EncodingStrategy
from ffmpeg_toolkit.core.executor import FFmpegExecutor
from ffmpeg_toolkit.features.converter import ConvertConfig, VideoConverter


@pytest.fixture
def mock_executor():
    return MagicMock(spec=FFmpegExecutor)


@pytest.fixture
def encoding_strategy():
    return EncodingStrategy()


@pytest.fixture
def converter(mock_executor, encoding_strategy):
    return VideoConverter(mock_executor, encoding_strategy)


class TestVideoConverter:
    def test_convert_success_gpu(self, converter, mock_executor):
        mock_executor.execute.return_value = (True, "處理完成")

        config = ConvertConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.mkv"),
            encoding="libx264",
        )
        success, message = converter.convert(config)

        assert success is True
        # 應該先嘗試 GPU (h264_nvenc)
        cmd = mock_executor.execute.call_args[0][0]
        assert "h264_nvenc" in cmd.codec_args

    def test_convert_fallback_to_cpu(self, converter, mock_executor):
        mock_executor.execute.side_effect = [
            (False, "No NVENC capable devices found"),
            (True, "處理完成"),
        ]

        config = ConvertConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.mkv"),
            encoding="libx264",
        )
        success, message = converter.convert(config)

        assert success is True
        assert mock_executor.execute.call_count == 2
        # 第二次應該用 CPU (libx264)
        cmd = mock_executor.execute.call_args[0][0]
        assert "libx264" in cmd.codec_args

    def test_convert_with_crf(self, converter, mock_executor):
        mock_executor.execute.return_value = (True, "處理完成")

        config = ConvertConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.mp4"),
            encoding="libx264",
            crf=18,
        )
        converter.convert(config)

        cmd = mock_executor.execute.call_args[0][0]
        assert "18" in cmd.codec_args

    def test_convert_h265(self, converter, mock_executor):
        mock_executor.execute.return_value = (True, "處理完成")

        config = ConvertConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.mp4"),
            encoding="libx265",
        )
        converter.convert(config)

        cmd = mock_executor.execute.call_args[0][0]
        assert "hevc_nvenc" in cmd.codec_args

    def test_convert_all_fail(self, converter, mock_executor):
        mock_executor.execute.side_effect = [
            (False, "No NVENC capable devices found"),
            (False, "Disk full"),
        ]

        config = ConvertConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.mkv"),
            encoding="libx264",
        )
        success, message = converter.convert(config)

        assert success is False


class TestVideoConverterHwAccel:
    def test_convert_with_qsv(self, mock_executor, encoding_strategy):
        """QSV 模式使用 -global_quality 而非 -crf"""
        mock_executor.execute.return_value = (True, "處理完成")
        converter = VideoConverter(mock_executor, encoding_strategy)

        config = ConvertConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.mp4"),
            encoding="libx264",
            hw_accel="qsv",
            crf=23,
        )
        success, _ = converter.convert(config)

        assert success is True
        cmd = mock_executor.execute.call_args[0][0]
        codec_args_str = " ".join(cmd.codec_args)
        assert "h264_qsv" in codec_args_str
        assert "-global_quality" in codec_args_str
        assert "-crf" not in codec_args_str

    def test_convert_with_nvenc(self, mock_executor, encoding_strategy):
        """NVENC 模式使用 -cq 而非 -crf"""
        mock_executor.execute.return_value = (True, "處理完成")
        converter = VideoConverter(mock_executor, encoding_strategy)

        config = ConvertConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.mp4"),
            encoding="libx264",
            hw_accel="nvenc",
            crf=23,
        )
        success, _ = converter.convert(config)

        assert success is True
        cmd = mock_executor.execute.call_args[0][0]
        codec_args_str = " ".join(cmd.codec_args)
        assert "h264_nvenc" in codec_args_str
        assert "-cq" in codec_args_str

    def test_convert_cpu_mode(self, mock_executor, encoding_strategy):
        """CPU 模式只嘗試 CPU 編碼器"""
        mock_executor.execute.return_value = (True, "處理完成")
        converter = VideoConverter(mock_executor, encoding_strategy)

        config = ConvertConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.mp4"),
            encoding="libx264",
            hw_accel="cpu",
            crf=23,
        )
        success, _ = converter.convert(config)

        assert success is True
        cmd = mock_executor.execute.call_args[0][0]
        assert "libx264" in cmd.codec_args
        assert mock_executor.execute.call_count == 1

    def test_convert_qsv_fallback_to_cpu(self, mock_executor, encoding_strategy):
        """QSV 失敗回退到 CPU"""
        mock_executor.execute.side_effect = [
            (False, "Error initializing an MFX session"),
            (True, "處理完成"),
        ]
        converter = VideoConverter(mock_executor, encoding_strategy)

        config = ConvertConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.mp4"),
            encoding="libx264",
            hw_accel="qsv",
            crf=23,
        )
        success, _ = converter.convert(config)

        assert success is True
        assert mock_executor.execute.call_count == 2
        cmd = mock_executor.execute.call_args[0][0]
        assert "libx264" in cmd.codec_args
        assert "-crf" in cmd.codec_args
