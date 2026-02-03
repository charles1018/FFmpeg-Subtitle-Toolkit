"""
測試 EncodingStrategy 編碼策略模組
"""

import pytest

from ffmpeg_toolkit.core.encoding import EncodingStrategy


class TestEncodingStrategy:
    """測試 EncodingStrategy 類別"""

    def test_h264_fallback_order(self):
        """測試 H.264 編碼器回退順序"""
        strategy = EncodingStrategy()
        codecs = list(strategy.get_codecs("libx264"))

        assert codecs == ["h264_nvenc", "libx264"]

    def test_h265_fallback_order(self):
        """測試 H.265 編碼器回退順序"""
        strategy = EncodingStrategy()
        codecs = list(strategy.get_codecs("libx265"))

        assert codecs == ["hevc_nvenc", "libx265"]

    def test_nvenc_h264_fallback_order(self):
        """測試 NVENC H.264 編碼器回退順序"""
        strategy = EncodingStrategy()
        codecs = list(strategy.get_codecs("h264_nvenc"))

        assert codecs == ["h264_nvenc", "libx264"]

    def test_nvenc_h265_fallback_order(self):
        """測試 NVENC H.265 編碼器回退順序"""
        strategy = EncodingStrategy()
        codecs = list(strategy.get_codecs("hevc_nvenc"))

        assert codecs == ["hevc_nvenc", "libx265"]

    def test_unknown_codec_no_fallback(self):
        """測試未知編碼器（無回退）"""
        strategy = EncodingStrategy()
        codecs = list(strategy.get_codecs("unknown_codec"))

        assert codecs == ["unknown_codec"]

    @pytest.mark.parametrize(
        "error_msg,should_fallback",
        [
            ("Cannot load nvEncodeAPI", True),
            ("No NVENC capable devices found", True),
            ("Invalid encoder", True),
            ("Unknown encoder 'h264_nvenc'", True),
            ("Impossible to convert between the formats", True),
            ("Error initializing", True),
            ("nvenc not available", True),
            ("Disk full", False),
            ("Invalid file format", False),
            ("Permission denied", False),
            ("No such file or directory", False),
        ],
    )
    def test_should_fallback(self, error_msg, should_fallback):
        """測試 NVENC 錯誤檢測"""
        strategy = EncodingStrategy()
        assert strategy.should_fallback(error_msg) == should_fallback

    def test_should_fallback_case_insensitive(self):
        """測試 NVENC 錯誤檢測（不分大小寫）"""
        strategy = EncodingStrategy()

        assert strategy.should_fallback("CANNOT LOAD NVENCODEAPI")
        assert strategy.should_fallback("no nvenc capable devices found")
        assert strategy.should_fallback("NvEnc Not Available")
