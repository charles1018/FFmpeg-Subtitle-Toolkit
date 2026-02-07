"""
影片資訊查看模組測試
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from ffmpeg_toolkit.features.media_info import MediaInfo, MediaInfoReader


@pytest.fixture
def reader():
    return MediaInfoReader()


@pytest.fixture
def sample_ffprobe_output():
    return json.dumps(
        {
            "format": {
                "format_long_name": "QuickTime / MOV",
                "duration": "125.5",
                "size": "52428800",
                "bit_rate": "3341672",
            },
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "30/1",
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "sample_rate": "48000",
                    "channels": 2,
                },
            ],
        }
    )


class TestMediaInfoReader:
    @patch("ffmpeg_toolkit.features.media_info.subprocess.run")
    def test_read_success(self, mock_run, reader, sample_ffprobe_output, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout=sample_ffprobe_output, stderr="")

        video_file = tmp_path / "test.mp4"
        video_file.write_text("mock")

        success, info, error = reader.read(video_file)

        assert success is True
        assert info is not None
        assert info.format_name == "QuickTime / MOV"
        assert info.duration == 125.5
        assert info.size == 52428800
        assert info.bit_rate == 3341672
        assert len(info.streams) == 2

    @patch("ffmpeg_toolkit.features.media_info.subprocess.run")
    def test_read_failure(self, mock_run, reader, tmp_path):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error: invalid file")

        video_file = tmp_path / "bad.mp4"
        video_file.write_text("mock")

        success, info, error = reader.read(video_file)

        assert success is False
        assert info is None
        assert "ffprobe" in error

    def test_format_info(self, reader):
        info = MediaInfo(
            format_name="MPEG-4",
            duration=3661.5,
            size=104857600,
            bit_rate=2000000,
            streams=[
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "24/1",
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "sample_rate": "44100",
                    "channels": 2,
                },
            ],
        )

        result = reader.format_info(info)

        assert "MPEG-4" in result
        assert "01:01:01" in result
        assert "100.00 MB" in result
        assert "2000 kbps" in result
        assert "h264" in result
        assert "1920x1080" in result
        assert "24" in result
        assert "aac" in result
        assert "44100" in result

    def test_format_info_with_subtitle_stream(self, reader):
        info = MediaInfo(
            format_name="MKV",
            duration=60.0,
            size=1048576,
            bit_rate=1000000,
            streams=[
                {"codec_type": "subtitle", "codec_name": "srt"},
            ],
        )

        result = reader.format_info(info)
        assert "字幕串流" in result
        assert "srt" in result
