"""
Pytest 配置和共用 fixtures
"""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """建立臨時目錄"""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def mock_video_file(temp_dir):
    """建立模擬影片檔案"""
    video = temp_dir / "test_video.mp4"
    video.write_text("mock video content")
    return video


@pytest.fixture
def mock_subtitle_file(temp_dir):
    """建立模擬字幕檔案"""
    subtitle = temp_dir / "test_subtitle.srt"
    subtitle.write_text(
        """1
00:00:01,000 --> 00:00:05,000
這是測試字幕

2
00:00:06,000 --> 00:00:10,000
第二行字幕
"""
    )
    return subtitle


@pytest.fixture
def mock_output_file(temp_dir):
    """建立模擬輸出檔案路徑"""
    return temp_dir / "output.mp4"
