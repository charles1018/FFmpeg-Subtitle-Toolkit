"""
音訊提取模組測試
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ffmpeg_toolkit.core.executor import FFmpegExecutor
from ffmpeg_toolkit.features.audio_extractor import AUDIO_FORMATS, AudioExtractConfig, AudioExtractor


@pytest.fixture
def mock_executor():
    return MagicMock(spec=FFmpegExecutor)


@pytest.fixture
def extractor(mock_executor):
    return AudioExtractor(mock_executor)


class TestAudioExtractor:
    def test_extract_mp3(self, extractor, mock_executor):
        mock_executor.execute.return_value = (True, "處理完成")

        config = AudioExtractConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.mp3"),
            audio_format="MP3",
        )
        success, message = extractor.extract(config)

        assert success is True
        cmd = mock_executor.execute.call_args[0][0]
        assert "-vn" in cmd.codec_args
        assert "libmp3lame" in cmd.codec_args
        assert cmd.skip_audio_copy is True

    def test_extract_aac(self, extractor, mock_executor):
        mock_executor.execute.return_value = (True, "處理完成")

        config = AudioExtractConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.aac"),
            audio_format="AAC",
        )
        extractor.extract(config)

        cmd = mock_executor.execute.call_args[0][0]
        assert "aac" in cmd.codec_args
        assert "-b:a" in cmd.codec_args

    def test_extract_flac(self, extractor, mock_executor):
        mock_executor.execute.return_value = (True, "處理完成")

        config = AudioExtractConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.flac"),
            audio_format="FLAC",
        )
        extractor.extract(config)

        cmd = mock_executor.execute.call_args[0][0]
        assert "flac" in cmd.codec_args

    def test_extract_wav(self, extractor, mock_executor):
        mock_executor.execute.return_value = (True, "處理完成")

        config = AudioExtractConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.wav"),
            audio_format="WAV",
        )
        extractor.extract(config)

        cmd = mock_executor.execute.call_args[0][0]
        assert "pcm_s16le" in cmd.codec_args

    def test_extract_unsupported_format(self, extractor):
        config = AudioExtractConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.ogg"),
            audio_format="OGG",
        )
        success, message = extractor.extract(config)

        assert success is False
        assert "不支援" in message

    def test_extract_failure(self, extractor, mock_executor):
        mock_executor.execute.return_value = (False, "FFmpeg error")

        config = AudioExtractConfig(
            input_file=Path("input.mp4"),
            output_file=Path("output.mp3"),
        )
        success, message = extractor.extract(config)

        assert success is False


class TestAudioFormats:
    def test_all_formats_have_required_keys(self):
        for name, fmt in AUDIO_FORMATS.items():
            assert "ext" in fmt, f"{name} missing ext"
            assert "codec" in fmt, f"{name} missing codec"
            assert "extra" in fmt, f"{name} missing extra"
